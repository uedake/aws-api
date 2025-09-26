import json
import os

import yaml

from aws_cdk import Stack, Tags
from aws_cdk.aws_lambda import Code, Function, Runtime
from aws_cdk.aws_sns import Topic
from aws_cdk.aws_apigatewayv2 import CfnApi
from aws_cdk.aws_cognito import UserPoolClient

from constructs import Construct
from jsonschema import Draft202012Validator

from .creator.lambda_creator import LambdaCreator
from .creator.apigateway_creator import ApiGatewayCreator, CognitoRef
from .creator.sqs_creator import SQSCreator
from .creator.ecr_creator import ECRCreator
from .creator.batch_creator import BatchCreator
from .creator.s3_creator import S3Creator
from .creator.sns_creator import SNSCreator
from .creator.amplify_creator import AmplifyCreator

from .creator.reference_solver import ReferenceSolver


class WebSystemParam:
    ENV_BUCKET_KEY = "Bucket"
    ENV_BRANCH_KEY = "Branch"
    ENV_URL_KEY = "NotificationUrl"
    ENV_API_KEY = "API"
    ENV_NEXT_SQS_KEY = "NextSQS"

    def __init__(
        self,
        api_name: str,
        branch_spec_dict: dict[str, dict],
        ref: ReferenceSolver,
        *,
        root_path: str | None = None,
        default_runtime: str | None = None,
        repository_root: str | None = None,
        repository_token: str | None = None,
    ):
        self.api_name = api_name
        self.branch_spec_dict = branch_spec_dict
        self.ref = ref
        self.root_path = root_path
        self.default_runtime = default_runtime
        self.repository_root = repository_root
        self.repository_token = repository_token

    def resolve_path(self, path: str) -> str:
        if self.root_path is None:
            return path

        if os.path.isabs(path):
            return path
        else:
            return os.path.join(self.root_path, path)

    def construct_env_dict(
        self,
        branch_name: str | None = None,
        lambda_key: str | None = None,
        lambda_spec_dict: dict[str, dict] | None = None,
    ):
        env_dict = {}
        env_dict[self.ENV_API_KEY] = self.api_name
        if branch_name is not None:
            branch_spec = self.branch_spec_dict[branch_name]
            env_dict[self.ENV_BRANCH_KEY] = branch_name
            if "bucket" in branch_spec:
                env_dict[self.ENV_BUCKET_KEY] = branch_spec["bucket"]
            if "notification-url" in branch_spec:
                env_dict[self.ENV_URL_KEY] = branch_spec["notification-url"]

        if lambda_key is not None and lambda_spec_dict is not None:
            lambda_spec = lambda_spec_dict[lambda_key]
            if "queue_next" in lambda_spec:
                if lambda_spec["queue_next"] not in lambda_spec_dict:
                    raise Exception(
                        f"lambda '{lambda_spec["queue_next"]}' spec not found: requested by queue_next of `{lambda_key}`"
                    )
                else:
                    if "queue" not in lambda_spec_dict[lambda_spec["queue_next"]]:
                        raise Exception(
                            f"lambda '{lambda_spec["queue_next"]}' spec should have `queue` key: requested by queue_next of `{lambda_key}`"
                        )

                env_dict[self.ENV_NEXT_SQS_KEY] = self.get_queue_name(
                    branch_name, lambda_spec["queue_next"]
                )

        return env_dict

    def get_lambda_name(self, branch_name: str, lambda_key: str):
        name_prefix = (
            self.api_name
            if branch_name is None
            else "{}-{}".format(self.api_name, branch_name)
        )
        return "{}-{}".format(name_prefix, lambda_key)

    def get_queue_name(self, branch_name: str, lambda_key: str, dead=False):
        name_prefix = (
            self.api_name
            if branch_name is None
            else "{}-{}".format(self.api_name, branch_name)
        )
        queue_prefix = "{}-{}".format(name_prefix, lambda_key)

        if dead:
            return queue_prefix + "_dead"
        else:
            return queue_prefix + "_waiting"


class WebSystemStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        construct後にcreate()を呼び出すことで定義に従ってAWSリソースを生成します。
        """
        super().__init__(scope, construct_id, **kwargs)

    def create(
        self,
        spec_dict: dict,
        *,
        access_token: str | None = None,
        root_path: str | None = None,
        schema_path: str | None = None,
    ):
        print("-----------start reading specs------------")
        # schema_check
        if schema_path is not None:
            with open(schema_path) as f:
                json_schema = json.load(f)

            Draft202012Validator.check_schema(json_schema)
            Draft202012Validator(json_schema).validate(spec_dict)

        param = WebSystemParam(
            spec_dict["api_name"],
            spec_dict["branch"],
            ReferenceSolver(self, spec_dict.get("ref")),
            root_path=root_path,
            default_runtime=spec_dict.get("default_runtime"),
            repository_root=spec_dict.get("repository_root"),
            repository_token=access_token,
        )

        self._create(
            param,
            spec_dict["lambda_func"],
            apigw_spec=spec_dict.get("apigw"),
            s3_spec_dict=spec_dict.get("s3"),
            sns_spec_dict=spec_dict.get("sns"),
            batch_spec_dict=spec_dict.get("batch_func"),
            amplify_spec_dict=spec_dict.get("amplify"),
        )

        if "tags" in spec_dict:
            for key, val in spec_dict["tags"].items():
                Tags.of(self).add(key, val)

        print("----------- complete ------------")

    def _create(
        self,
        param: WebSystemParam,
        lambda_spec_dict: dict[str, dict],
        *,
        apigw_spec: dict | None = None,
        s3_spec_dict: dict[str, dict] | None = None,
        sns_spec_dict: dict[str, dict] | None = None,
        batch_spec_dict: dict[str, dict] | None = None,
        amplify_spec_dict: dict[str, dict] | None = None,
    ):
        """
        アプリのバックエンドとなるAPIとそのAPIを使用するWebAppを生成します。
        - 下記はbranch毎に1つのリソースを作成します。
          - s3
          - apigw(内部でbranch毎にstage設定)
          - amplify(内部でbranch毎にstage設定)
          - sns
          - ecr(内部でbranch設定)
        - 下記はbranch毎にリソースを別々に作成します。
          - lambda
          - sqs
          - batch

        parameters:
          root_path: spec_dict中で記載されている相対パスにおけるルートパスを設定します。
                     Noneの場合はapp.pyが存在するフォルダからの相対パスとみなされます。
        """
        # must create topic, amplify, apigw, lambda in this order
        # because depedency exists.
        # - amplify may use topic as "deploy_event_sns"
        # - apigw may use amplify if using cognito_auth.
        #   - apigw needs to set user pool client for its amplify app as authorizer
        # - lambda may use apigw
        #   - lambda needs to set policy for apigw access.

        # create topics (for each topic spec)
        if sns_spec_dict is not None:
            topic_dict = self._craete_sns(
                param,
                sns_spec_dict,
            )
            param.ref.set_topic(topic_dict)

        if amplify_spec_dict is not None:
            if param.repository_token is None:
                raise Exception("need repository_token of github for amplify")
            if param.repository_root is None:
                raise Exception("need repository_root of github for amplify")
            client_dict = self._create_app(
                param,
                amplify_spec_dict,
            )
            param.ref.set_cognito_client(client_dict)

        if apigw_spec is not None:
            api = self._create_apigw(
                param,
                apigw_spec,
            )
            param.ref.set_api(api)

        if s3_spec_dict is not None:
            self._create_s3(s3_spec_dict)

        # create repository (for each batch_func spec)
        if batch_spec_dict is not None:
            for batch_key in batch_spec_dict.keys():
                ECRCreator(self, "{}-{}".format(param.api_name, batch_key))

        # for each branch
        for branch_name in param.branch_spec_dict:

            # create lambdas (for each branch and each lambda_func spec)
            lambda_func_dict = self._create_lambda(
                param,
                lambda_spec_dict,
                branch_name=branch_name,
                apigw_spec=apigw_spec,
            )

            # create batchs (for each branch and each batch_func spec)
            if batch_spec_dict is not None:
                self._create_batch(
                    param,
                    branch_name,
                    batch_spec_dict,
                    lambda_func_dict,
                )

    def _create_app(
        self,
        param: WebSystemParam,
        amplify_spec_dict: dict[str, dict],
    ) -> dict[str, UserPoolClient]:
        client_dict: dict[str, UserPoolClient] = {}
        for app_name, app_spec in amplify_spec_dict.items():
            user_pool_id = (
                param.ref.cognito[app_spec["cognito_auth"]]["user_pool_id"]
                if "cognito_auth" in app_spec
                else None
            )
            amplify = AmplifyCreator(
                self,
                app_name,
                {
                    branch_name: {
                        "stage": branch_spec["amplify_type"],
                        "env": param.construct_env_dict(branch_name),
                    }
                    for branch_name, branch_spec in param.branch_spec_dict.items()
                },
                param.repository_root,
                param.repository_token,
                app_spec["domain"],
                description=app_spec.get("description"),
            )
            if user_pool_id is not None:
                client = amplify.create_cognito_login_page(user_pool_id)
                client_dict[app_name] = client
            if "deploy_event_sns" in app_spec:
                topic = param.ref.get_topic(app_spec["deploy_event_sns"])
                amplify.create_event_bridge(topic.topic_arn)
        return client_dict

    def _create_s3(
        self,
        s3_spec_dict: dict[str, dict],
    ):
        for bucket_name, s3_spec in s3_spec_dict.items():
            S3Creator(
                self,
                bucket_name,
                public_read=s3_spec.get("public_read"),
                website_hosting=s3_spec.get("website_hosting"),
            )

    def _create_apigw(
        self,
        param: WebSystemParam,
        apigw_spec: dict,
    ) -> CfnApi:
        lambda_integration_spec: dict[str, dict] = apigw_spec["lambda_integration"]

        for route_spec in lambda_integration_spec.values():
            if "route_openapi" in route_spec:
                route_list = []
                with open(param.resolve_path(route_spec["route_openapi"])) as f:
                    data = yaml.safe_load(f)
                    for path, method_dict in data["paths"].items():
                        for method in method_dict:
                            route_list.append(f"{method.upper()} {path}")
                route_spec["route"] = route_list

        api_creator = (
            ApiGatewayCreator(
                self,
                param.api_name,
                apigw_spec.get("description"),
            )
            .add_stages(
                {
                    branch_spec["apigw_stage"]: branch_name
                    for branch_name, branch_spec in param.branch_spec_dict.items()
                }
            )
            .add_lambda_integrations(
                lambda_integration_spec,
                cognito=CognitoRef(
                    user_pool_dict=param.ref.cognito,
                    client_id_dict=param.ref.get_cognito_client_id_dict(),
                ),
            )
        )
        return api_creator.api

    def _craete_sns(
        self,
        param: WebSystemParam,
        sns_spec_dict: dict[str, dict],
    ) -> dict[str, Topic]:
        topic_dict = {}
        for topic_key, sns_spec in sns_spec_dict.items():
            sns = SNSCreator(
                self,
                "{}-{}".format(param.api_name, topic_key),
                sns_spec.get("description"),
            ).called_by_event_bridge()
            topic_dict[topic_key] = sns.topic

            if "lambda_func" in sns_spec:
                lambda_spec_dict = sns_spec["lambda_func"]

                # create lambdas (for each lambda_func spec)
                self._create_lambda(
                    param,
                    lambda_spec_dict,
                    sender_topic=sns.topic,
                )

        return topic_dict

    def _create_lambda(
        self,
        param: WebSystemParam,
        lambda_spec_dict: dict[str, dict],
        *,
        branch_name: str | None = None,
        apigw_spec: dict | None = None,
        sender_topic: Topic | None = None,
    ) -> dict[str, Function]:

        layer_dict = param.ref.lambda_layer
        lambda_func_dict = {}
        for lambda_key, lambda_spec in lambda_spec_dict.items():
            lambda_name = param.get_lambda_name(branch_name, lambda_key)

            layers = (
                [layer_dict[layer_id] for layer_id in lambda_spec["layer_list"]]
                if "layer_list" in lambda_spec
                else None
            )

            lambda_creator = LambdaCreator(
                self,
                lambda_name,
                runtime=getattr(
                    Runtime,
                    lambda_spec.get("runtime", ""),
                    getattr(Runtime, param.default_runtime, None),
                ),
                code=(
                    Code.from_asset(param.resolve_path(lambda_spec["code"]))
                    if "code" in lambda_spec
                    else None
                ),
                layers=layers,
                env_dict=param.construct_env_dict(
                    branch_name, lambda_key, lambda_spec_dict
                ),
                test_schema_path=(
                    param.resolve_path(lambda_spec.get("test"))
                    if "test" in lambda_spec
                    else None
                ),
                timeout=lambda_spec.get("timeout"),
                memory_size=lambda_spec.get("memory_size"),
                storage_size=lambda_spec.get("storage_size"),
            )
            if (
                apigw_spec is not None
                and lambda_key in apigw_spec["lambda_integration"]
            ):
                lambda_creator.called_by_apigateway(param.ref.get_apigw_arn())

            if sender_topic is not None:
                lambda_creator.called_by_sns(sender_topic)

            if "queue" in lambda_spec:
                sqs_spec = lambda_spec["queue"]
                additional_timeout = sqs_spec.get("additional_timeout", 10)
                base_timeout = lambda_spec.get("timeout", 3)

                sqs_creator = SQSCreator(
                    self,
                    param.get_queue_name(branch_name, lambda_key),
                    param.get_queue_name(branch_name, lambda_key, True),
                    visibility_timeout_sec=base_timeout + additional_timeout,
                )
                lambda_creator.called_by_sqs(sqs_creator.queue)
            lambda_func_dict[lambda_key] = lambda_creator.func
        return lambda_func_dict

    def _create_batch(
        self,
        param: WebSystemParam,
        branch_name: str,
        batch_spec_dict: dict[str, dict],
        lambda_func_dict: dict[str, Function],
    ):
        if param.ref.vpc is None:
            print("[Warn] cannot create batch func: vpc is not defined in spec")
            return

        env_dict = param.construct_env_dict(branch_name)
        for batch_key, batch_spec in batch_spec_dict.items():
            BatchCreator(
                self,
                "{}-{}-{}".format(param.api_name, branch_name, batch_key),
                "{}.dkr.ecr.{}.amazonaws.com/{}-{}:{}".format(
                    self.account,
                    self.region,
                    param.api_name,
                    batch_key,
                    branch_name,
                ),
                batch_spec["maxv_cpus"],
                param.ref.vpc["subnet_id_list"],
                param.ref.vpc["security_group_id"],
                queue_state_lambda=lambda_func_dict[
                    batch_spec.get("queue_state_lambda")
                ],
                env_dict=env_dict,
                memory=batch_spec.get("memory"),
                vcpu=batch_spec.get("vcpu"),
            )
