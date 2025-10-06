import os

from aws_cdk import Stack
from aws_cdk.aws_amplify import CfnApp, CfnBranch, CfnDomain
from aws_cdk.aws_sns import Topic
from aws_cdk.aws_events import Rule, EventPattern
from aws_cdk.aws_events_targets import SnsTopic
from aws_cdk.aws_cognito import UserPool, UserPoolClient, OAuthSettings, OAuthFlows

from .iam_creator import IAMCreator
from aws_cdk.aws_cognito import (
    CfnIdentityPool,
    CfnIdentityPoolRoleAttachment,
    CfnManagedLoginBranding
)
from aws_cdk.aws_iam import Role


class AmplifyCreator:
    def __init__(
        self,
        scope: Stack,
        app_name: str,
        branch_dict: dict,
        repository_root: str,
        repository_token: str,
        domain_name: str,
        *,
        description: str | None = None,
    ) -> None:
        self.scope = scope
        self.branch_dict = branch_dict
        self.domain_name = domain_name

        app = CfnApp(
            self.scope,
            app_name,
            name=app_name,
            access_token=repository_token,
            repository=f"{repository_root}/{app_name}",
            description=description,
        )
        sub_domain_list = []
        branch_list = []
        for branch_name, stage_dict in branch_dict.items():
            branch = CfnBranch(
                self.scope,
                f"{app_name}-{branch_name}",
                app_id=app.attr_app_id,
                branch_name=branch_name,
                stage=stage_dict["stage"],
                environment_variables=[
                    {"name": key, "value": val}
                    for key, val in stage_dict["env"].items()
                ],
            )
            branch_list.append(branch)
            sub_domain_list.append(
                CfnDomain.SubDomainSettingProperty(
                    branch_name=branch_name,
                    prefix=branch_name,
                )
            )
        domain = CfnDomain(
            self.scope,
            f"{app_name}-domain",
            app_id=app.attr_app_id,
            domain_name=f"{app_name}.{domain_name}",
            sub_domain_settings=sub_domain_list,
        )
        for branch in branch_list:
            domain.node.add_dependency(branch)
        self.app = app

    def create_cognito_login_page(self, user_pool_id: str) -> UserPoolClient:
        user_pool = UserPool.from_user_pool_id(self.scope, "user_pool", user_pool_id)
        callback_urls = ["http://localhost:3000/"] + [
            f"https://{branch}.{self.app.name}.{self.domain_name}/"
            for branch in self.branch_dict.keys()
        ]
        user_pool_client = UserPoolClient(
            self.scope,
            f"{self.app.name}-client",
            user_pool_client_name=f"{self.app.name}-client",
            user_pool=user_pool,
            o_auth=OAuthSettings(
                flows=OAuthFlows(authorization_code_grant=True),
                callback_urls=callback_urls,
                logout_urls=callback_urls,
            ),
        )
        CfnManagedLoginBranding(
            self.scope,
            f"{self.app.name}-brand",
            user_pool_id=user_pool.user_pool_id,
            client_id=user_pool_client.user_pool_client_id,
            use_cognito_provided_values=True,
        )

        return user_pool_client

    def create_event_bridge(
        self,
        topic_arn: str,
    ) -> SnsTopic:

        topic = SnsTopic(
            Topic.from_topic_arn(self.scope, "amplify-notification", topic_arn)
        )
        _ = Rule(
            self.scope,
            f"{self.app.name}-rule",
            rule_name=f"amplify-{self.app.name}-notification",
            event_pattern=EventPattern(
                detail={
                    "appId": [self.app.attr_app_id],
                    "branchName": list(self.branch_dict.keys()),
                    "jobStatus": ["SUCCEED", "FAILED", "STARTED"],
                },
                detail_type=["Amplify Deployment Status Change"],
                source=["aws.amplify"],
            ),
            targets=[topic],
        )
        # policy=PolicyStatement(
        #     sid="AWSEvents_Allow",
        #     effect=Effect.ALLOW,
        #     principals=[ServicePrincipal("events.amazonaws.com")],
        #     actions=["sns:Publish"],
        #     resources=[rule.rule_arn]
        #     )
        # topic.add_to_resource_policy(policy)
        return topic

    def create_cognito_idpool(
        self,
        policy_json_list: list[str],
        service_name: str,
        env: dict[str, str],
    ):
        for branch_name in self.branch_dict:
            identity_pool_name = f"{self.app.name}-{branch_name}-pool"
            identity_pool = CfnIdentityPool(
                self.scope,
                identity_pool_name,
                allow_unauthenticated_identities=False,
                identity_pool_name=identity_pool_name,
            )

            role: Role = IAMCreator(
                self.scope,
                service_name,
                env,
            ).cretae_role_for_identity_pool(
                f"{self.app.name}-{branch_name}-authenticated-role",
                identity_pool,
                policy_json_list,
                branch_name,
            )

            CfnIdentityPoolRoleAttachment(
                self.scope,
                f"{self.app.name}-{branch_name}-role-attach",
                identity_pool_id=identity_pool.ref,
                roles={"authenticated": role.role_arn},
            )
