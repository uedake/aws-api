from __future__ import annotations
from aws_cdk import Stack
from aws_cdk.aws_apigatewayv2 import (
    CfnApi,
    CfnStage,
    CfnRoute,
    CfnIntegration,
    CfnAuthorizer,
    DomainName,
    EndpointType,
    CfnApiMapping,
)
from aws_cdk.aws_logs import LogGroup
from aws_cdk.aws_route53 import ARecord, RecordTarget, HostedZone
from aws_cdk.aws_route53_targets import ApiGatewayv2DomainProperties
from aws_cdk.aws_certificatemanager import Certificate, CertificateValidation

from .reference_solver import NameSolver


class CognitoRef:
    def __init__(
        self,
        user_pool_dict: dict[str, str],
        client_id_dict: dict[str, str],
    ):
        self.user_pool_dict = user_pool_dict
        self.client_id_dict = client_id_dict

    def get_authorizer_name(
        self,
        auth_spec,
    ):
        assert auth_spec["user"] in self.user_pool_dict

        return "auth-{}-{}".format(auth_spec["user"], auth_spec["app"])

    def get_jwt_configuration(
        self,
        auth_spec,
    ) -> CfnAuthorizer.JWTConfigurationProperty:
        assert auth_spec["user"] in self.user_pool_dict
        client_id = self.client_id_dict[auth_spec["app"]]
        user_pool_id = self.user_pool_dict[auth_spec["user"]]["user_pool_url"]
        return CfnAuthorizer.JWTConfigurationProperty(
            audience=[client_id],
            issuer=user_pool_id,
        )


class ApiGatewayCreator:
    ##############################################
    STAGE_VARIABLE_BRANCH = "branch"
    ##############################################

    def __init__(
        self,
        scope: Stack,
        api_name: str,
        api_description: str | None,
    ) -> None:
        self.scope = scope
        self.solver = NameSolver(scope, api_name)

        self.api = CfnApi(
            self.scope,
            api_name,
            name=api_name,
            description=api_description,
            protocol_type="HTTP",
            cors_configuration=CfnApi.CorsProperty(
                allow_headers=["*"],
                allow_methods=["GET", "POST", "HEAD"],
                allow_origins=["*"],
            ),
        )

    def _create_domain(self, zone_name: str):
        hosted_zone = HostedZone.from_lookup(
            self.scope, f"{self.api.name}-Zone", domain_name=zone_name
        )
        cert = Certificate(
            self.scope,
            f"{self.api.name}-Cert",
            domain_name=f"{self.api.name}.{zone_name}",
            validation=CertificateValidation.from_dns(hosted_zone),
        )
        domain = DomainName(
            self.scope,
            f"{self.api.name}-CustomDomain",
            domain_name=f"{self.api.name}.{zone_name}",
            certificate=cert,
            endpoint_type=EndpointType.REGIONAL,
        )

        ARecord(
            self.scope,
            f"{self.api.name}-aliasRecord",
            zone=hosted_zone,
            record_name=self.api.name,
            target=RecordTarget.from_alias(
                ApiGatewayv2DomainProperties(
                    domain.regional_domain_name,
                    domain.regional_hosted_zone_id,
                )
            ),
        )

        return domain

    def add_stages(
        self, stages_dict: dict | None = None, *, zone_name: str | None = None
    ) -> ApiGatewayCreator:
        domain_name = self._create_domain(zone_name) if zone_name is not None else None
        if stages_dict is None:
            stages_dict = {"$default": "master"}
        for stage_name, branch in stages_dict.items():
            self._create_stage(stage_name, branch, domain_name)
        return self

    def add_lambda_integrations(
        self,
        lambda_integration_spec: dict[str, dict],
        *,
        cognito: CognitoRef | None = None,
    ) -> ApiGatewayCreator:

        authorizer_dict = {}
        for route_spec in lambda_integration_spec.values():
            if "cognito_auth" in route_spec:
                assert cognito is not None
                auth_spec = route_spec["cognito_auth"]
                authorizer_name = cognito.get_authorizer_name(auth_spec)
                if authorizer_name not in authorizer_dict:
                    authorizer_dict[authorizer_name] = CfnAuthorizer(
                        self.scope,
                        authorizer_name,
                        api_id=self.api.ref,
                        authorizer_type="JWT",
                        name=authorizer_name,
                        identity_source=["$request.header.Authorization"],
                        jwt_configuration=cognito.get_jwt_configuration(auth_spec),
                    )

        for lambda_key, route_spec in lambda_integration_spec.items():

            self._create_lambda_integration(
                self.solver.get_lambda_name(
                    lambda_key, "${stageVariables." + self.STAGE_VARIABLE_BRANCH + "}"
                ),  # stage変数を参照して決まるlambda名
                route_spec["route"],
                (
                    authorizer_dict[
                        cognito.get_authorizer_name(route_spec["cognito_auth"])
                    ]
                    if "cognito_auth" in route_spec
                    else None
                ),
            )
        return self

    def _create_stage(
        self, stage_name: str, branch: str, domain: DomainName | None = None
    ) -> None:
        log_group = LogGroup(
            self.scope,
            f"{self.api.name}_{stage_name}_log",
            log_group_name=f"{self.api.name}-{branch}"
        )

        format = "$context.identity.sourceIp,$context.requestTime,$context.httpMethod,$context.routeKey,$context.protocol,$context.status,$context.responseLength,$context.requestId"
        stage = CfnStage(
            self.scope,
            f"{self.api.name}_{stage_name}",
            api_id=self.api.ref,
            stage_name=stage_name,
            auto_deploy=True,
            stage_variables={self.STAGE_VARIABLE_BRANCH: branch},
            access_log_settings=CfnStage.AccessLogSettingsProperty(
                destination_arn=log_group.log_group_arn,
                format=format,
            ),
        )
        stage.add_dependency(log_group.node.default_child)

        if domain is not None:
            mapping = CfnApiMapping(
                self.scope,
                "{}_{}_mapping".format(self.api.name, stage_name),
                api_id=self.api.ref,
                domain_name=domain.name,
                stage=stage_name,
                api_mapping_key=stage_name if stage_name != "$default" else None,
            )
            mapping.add_dependency(domain.node.default_child)
            mapping.add_dependency(stage)

    def _create_lambda_integration(
        self,
        lambda_name: str,
        route_key_list: list[str],
        authorizer: CfnAuthorizer | None = None,
    ) -> None:

        integration = CfnIntegration(
            self.scope,
            f"{lambda_name}-integration",
            api_id=self.api.ref,
            integration_type="AWS_PROXY",
            integration_uri="arn:aws:lambda:{}:{}:function:{}".format(
                self.scope.region, self.scope.account, lambda_name
            ),
            integration_method="GET",
            payload_format_version="2.0",
        )
        for route_key in route_key_list:
            CfnRoute(
                self.scope,
                "{}:{}".format(lambda_name, route_key),
                api_id=self.api.ref,
                target="integrations/" + integration.ref,
                route_key=route_key,
                authorizer_id=authorizer.ref if authorizer is not None else None,
                authorization_type="JWT" if authorizer is not None else None,
            )
        return integration
