from __future__ import annotations

import json
import os

from aws_cdk import Stack
from aws_cdk.aws_iam import Policy, PolicyDocument, Role, FederatedPrincipal
from aws_cdk.aws_cognito import CfnIdentityPool


class IAMCreator:
    def __init__(
        self,
        scope: Stack,
        service_name: str,
        env: dict,
    ) -> None:
        self.scope = scope
        self.service_name = service_name
        self.env = env

        self.managed_policy_dict: dict[str, Policy] = {}
        self.role_dict: dict[str, Role] = {}

    def cretae_role_for_identity_pool(
        self,
        role_name: str,
        identity_pool: CfnIdentityPool,
        policy_json_list: list[str],
        branch_name: str,
    ) -> Role:
        role = Role(
            self.scope,
            role_name,
            role_name=role_name,
            assumed_by=FederatedPrincipal(
                "cognito-identity.amazonaws.com",
                {
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": identity_pool.ref
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated"
                    },
                },
                "sts:AssumeRoleWithWebIdentity",
            ),
            inline_policies={
                os.path.basename(path): PolicyDocument.from_json(
                    self.read_policy_json(
                        path, self.service_name, branch_name, self.env
                    )
                )
                for path in policy_json_list
            },
        )
        self.role_dict[role_name] = role
        return role

    def create_managed_policy(
        self,
        policy_name: str,
        json_path: str,
        branch_name: str,
    ):
        policy = Policy(
            self.scope,
            policy_name,
            policy_name=policy_name,
            document=PolicyDocument.from_json(
                self.read_policy_json(
                    json_path, self.service_name, branch_name, self.env
                )
            ),
        )
        self.managed_policy_dict[policy_name] = policy
        return policy

    @staticmethod
    def read_policy_json(
        json_path: str, service_name: str, branch_name: str, env: dict
    ):
        """
        policy定義ファイル中の下記は文字列置換されます
        - {$account}: AWSアカウント名で置換します
        - {$region}: AWSリージョン名で置換します
        - {$service}: 引数で指定するservice_nameで置換します
        - {$branch}: 引数で指定するbranch_nameで置換します
        """

        with open(json_path) as f:
            text = f.read()
            replaced_text = (
                text.replace("{$service}", service_name)
                .replace("{$branch}", branch_name)
                .replace("{$account}", env["account"])
                .replace("{$region}", env["region"])
            )
            return json.loads(replaced_text)
