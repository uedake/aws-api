from aws_cdk import Stack
from aws_cdk.aws_lambda import LayerVersion, ILayerVersion
from aws_cdk.aws_apigatewayv2 import CfnApi
from aws_cdk.aws_sns import Topic
from aws_cdk.aws_cognito import UserPoolClient

from ..awsutil.aws_check_util import LambdaLayerChecker


class ReferenceSolver:
    def __init__(
        self,
        scope: Stack,
        ref_spec: dict[str, dict] | None = None,
    ):
        self.scope = scope
        self.lambda_layer = (
            self._solve_lambda_layer(ref_spec["lambda_layer"])
            if ref_spec is not None and "lambda_layer" in ref_spec
            else {}
        )
        self.cognito = (
            {
                user: {
                    **cognito_spec,
                    "user_pool_url": self._solve_user_pool_url(
                        cognito_spec["user_pool_id"]
                    ),
                }
                for user, cognito_spec in ref_spec["cognito"].items()
            }
            if ref_spec is not None and "cognito" in ref_spec
            else {}
        )
        self.vpc = ref_spec.get("vpc") if ref_spec is not None else None

        self.topic_dict: dict[str, Topic] = {}
        self.api = None
        self.client_dict: dict[str, UserPoolClient] = {}

    def set_topic(self, topic_dict: dict[str, Topic]):
        self.topic_dict = topic_dict

    def get_topic(self, topic_key: str) -> Topic:
        return self.topic_dict[topic_key]

    def set_api(self, api: CfnApi):
        self.api = api

    def get_apigw_arn(self) -> str:
        return "arn:aws:execute-api:{}:{}:{}/*/*/*".format(
            self.scope.region, self.scope.account, self.api.ref
        )

    def set_cognito_client(self, client_dict: dict[str, UserPoolClient]):
        self.client_dict = client_dict

    def get_cognito_client_id_dict(self):
        return {
            app_name: client.user_pool_client_id
            for app_name, client in self.client_dict.items()
        }

    def _solve_user_pool_url(self, user_pool_id: str) -> str:
        return "https://cognito-idp.{}.amazonaws.com/{}".format(
            self.scope.region, user_pool_id
        )

    def _solve_lambda_layer(
        self,
        ref_layer_dict: dict[str, dict],
    ):
        # get lambda layer reference
        layer_dict: dict[str, ILayerVersion] = {}

        for layer_id, layer_arn_or_name in ref_layer_dict.items():
            _layer_version_arn = self._resolve_lambda_layer_arn(layer_arn_or_name)
            layer_dict[layer_id] = LayerVersion.from_layer_version_arn(
                self.scope,
                _layer_version_arn,
                layer_version_arn=_layer_version_arn,
            )
        return layer_dict

    def _resolve_lambda_layer_arn(self, arn_or_name: str):
        if arn_or_name.startswith("arn:"):
            return arn_or_name
        else:
            layer_name = arn_or_name
            ver = LambdaLayerChecker(layer_name).get_latest_version()
            return "arn:aws:lambda:{}:{}:layer:{}:{}".format(
                self.scope.region, self.scope.account, layer_name, ver
            )
