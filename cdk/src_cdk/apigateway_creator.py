from __future__ import annotations
from aws_cdk import Stack
from aws_cdk.aws_apigatewayv2 import (
    CfnApi,
    CfnStage,
    CfnRoute,
    CfnIntegration,
    CfnAuthorizer,
    CfnDomainName,
    CfnApiMapping,
)
from aws_cdk.aws_route53 import ARecord, RecordTarget, HostedZone, IHostedZone
from aws_cdk.aws_route53_targets import ApiGatewayv2DomainProperties


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

    def add_stages(
        self,
        stages_dict: dict | None = None,
        zone_id: str | None = None,
        zone_name: str | None = None,
        certificate_arn: str | None = None,
    ) -> ApiGatewayCreator:

        domain = (
            self._create_apigateway_domain(
                self.api.name,
                "{}.{}".format(self.api.name, zone_name),
                HostedZone.from_hosted_zone_attributes(
                    self.scope,
                    "hostedZone",
                    hosted_zone_id=zone_id,
                    zone_name=zone_name,
                ),
                certificate_arn=certificate_arn,
            )
            if zone_id is not None and zone_name is not None
            else None
        )

        if stages_dict is None:
            stages_dict = {"$default": "master"}
        for stage_name, branch in stages_dict.items():
            self._create_stage(stage_name, branch, domain)
        return self

    def add_lambda_integrations(
        self,
        route_key_list_dict: dict[str, list[str]],
        cognito_user_pool_url: str | None = None,
        cognito_client_id: str | None = None,
    ) -> ApiGatewayCreator:

        authorizer = (
            CfnAuthorizer(
                self.scope,
                "cognito-authorizer",
                api_id=self.api.ref,
                authorizer_type="JWT",
                name="cognito-authorizer",
                identity_source=["$request.header.Authorization"],
                jwt_configuration=CfnAuthorizer.JWTConfigurationProperty(
                    audience=cognito_client_id,
                    issuer=cognito_user_pool_url,
                ),
            )
            if cognito_client_id is not None and cognito_user_pool_url is not None
            else None
        )

        for lambda_name, route_key_list in route_key_list_dict.items():
            self._create_lambda_integration(lambda_name, route_key_list, authorizer)
        return self

    def _create_apigateway_domain(
        self,
        api_name: str,
        domain_name: str,
        zone: IHostedZone,
        *,
        certificate_arn: str | None = None,
    ) -> CfnDomainName:
        domain = CfnDomainName(
            self.scope,
            "{}_domain".format(api_name),
            domain_name=domain_name,
            domain_name_configurations=(
                [
                    CfnDomainName.DomainNameConfigurationProperty(
                        certificate_arn=certificate_arn,
                    )
                ]
                if certificate_arn is not None
                else None
            ),
        )
        _ = ARecord(
            self.scope,
            "{}_aliasRecord".format(api_name),
            zone=zone,
            record_name=domain_name,
            target=RecordTarget.from_alias(
                ApiGatewayv2DomainProperties(
                    domain.attr_regional_domain_name,
                    domain.attr_regional_hosted_zone_id,
                )
            ),
        )
        return domain

    def _create_stage(
        self, stage_name: str, branch: str, domain: CfnDomainName | None = None
    ) -> None:
        stage = CfnStage(
            self.scope,
            "{}_{}".format(self.api.name, stage_name),
            api_id=self.api.ref,
            stage_name=stage_name,
            auto_deploy=True,
            stage_variables={self.STAGE_VARIABLE_BRANCH: branch},
        )

        if domain is not None:
            mapping = CfnApiMapping(
                self.scope,
                "{}_{}_mapping".format(self.api.name, stage.stage_name),
                api_id=self.api.ref,
                domain_name=domain.domain_name,
                stage=stage.stage_name,
                api_mapping_key=branch,
            )
            mapping.add_dependency(domain)
            mapping.add_dependency(stage)

    def _create_lambda_integration(
        self,
        lambda_name: str,
        route_key_list: list[str],
        authorizer: CfnAuthorizer | None = None,
    ) -> None:
        integration_func_name = "{}-{}-{}".format(
            self.api.name,
            "${stageVariables." + self.STAGE_VARIABLE_BRANCH + "}",
            lambda_name,
        )

        integration = CfnIntegration(
            self.scope,
            integration_func_name,
            api_id=self.api.ref,
            integration_type="AWS_PROXY",
            integration_uri="arn:aws:lambda:{}:{}:function:{}".format(
                self.scope.region, self.scope.account, integration_func_name
            ),
            integration_method="GET",
            payload_format_version="2.0",
        )
        for route_key in route_key_list:
            CfnRoute(
                self.scope,
                "{}:{}".format(integration_func_name, route_key),
                api_id=self.api.ref,
                target="integrations/" + integration.ref,
                route_key=route_key,
                authorizer_id=authorizer.ref if authorizer is not None else None,
                authorization_type="JWT" if authorizer is not None else None,
            )
        return integration
