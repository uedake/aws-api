import json
import os

from aws_cdk import Stack
from aws_cdk.aws_lambda import Code, LayerVersion

from constructs import Construct
from jsonschema import Draft202012Validator

from .creator.lambda_creator import LambdaCreator
from .creator.apigateway_creator import ApiGatewayCreator
from .creator.sqs_creator import SQSCreator
from .creator.ecr_creator import ECRCreator
from .creator.batch_creator import BatchCreator
from .creator.s3_creator import S3Creator
from .awsutil.aws_check_util import LambdaLayerChecker


class APIStack(Stack):
    ENV_BUCKET_KEY = "Bucket"
    ENV_BRANCH_KEY = "Branch"
    ENV_API_KEY = "API"
    ENV_NEXT_SQS_KEY = "NextSQS"

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

    def create(
        self,
        api_spec: dict,
        *,
        root_path: str | None = None,
        schema_path: str | None = None,
    ):
        stage_spec_dict = (
            api_spec["stage"]
            if "stage" in api_spec
            else {
                "$default": {
                    "branch": "master",
                },
            }
        )
        """
        root_pathにはspec_dict中で記載されているパスが相対パス表記である場合のルートパスを設定します。
        Noneの場合はapp.pyが存在するフォルダからの相対パスとみなされます。
        """

        # schema_check
        if schema_path is not None:
            with open(schema_path) as f:
                json_schema = json.load(f)

            Draft202012Validator.check_schema(json_schema)
            Draft202012Validator(json_schema).validate(api_spec)

        self._create(
            api_spec["name"],
            stage_spec_dict,
            s3_spec_dict=api_spec.get("s3"),
            apigw_spec=api_spec.get("apigw"),
            lambda_spec_dict=api_spec.get("lambda_func"),
            sqs_spec_dict=api_spec.get("sqs_for_lambda"),
            batch_spec_dict=api_spec.get("batch_func"),
            ref_spec=api_spec.get("ref"),
            root_path=root_path,
        )

    @staticmethod
    def _resolve_path(path: str, root_path: str | None = None) -> str:
        if root_path is None:
            return path

        if os.path.isabs(path):
            return path
        else:
            return os.path.join(root_path, path)

    def _resolve_lambda_layer_arn(self, arn_or_name: str):
        if arn_or_name.startswith("arn:"):
            return arn_or_name
        else:
            layer_name = arn_or_name
            ver = LambdaLayerChecker(layer_name).get_latest_version()
            return "arn:aws:lambda:{}:{}:layer:{}:{}".format(
                self.region, self.account, layer_name, ver
            )

    def _create(
        self,
        api_name: str,
        stage_spec_dict: dict,
        *,
        s3_spec_dict: dict | None = None,
        apigw_spec: dict | None = None,
        sqs_spec_dict: dict | None = None,
        lambda_spec_dict: dict | None | None,
        batch_spec_dict: dict | None = None,
        ref_spec: dict | None = None,
        root_path: str | None = None,
    ):
        ref_layer_dict = ref_spec.get("lambda_layer") if ref_spec is not None else None
        ref_vpc = ref_spec.get("vpc") if ref_spec is not None else None

        # ceate s3
        if s3_spec_dict is not None:
            for bucket_name, s3_spec in s3_spec_dict.items():
                S3Creator(
                    self,
                    bucket_name,
                    public_read=s3_spec.get("public_read"),
                    website_hosting=s3_spec.get("website_hosting"),
                )
        # create apigateway
        if apigw_spec is not None:
            api_creator = (
                ApiGatewayCreator(
                    self,
                    api_name,
                    apigw_spec["description"],
                )
                .add_stages(
                    {
                        stage_name: stage_spec["branch"]
                        for stage_name, stage_spec in stage_spec_dict.items()
                    }
                )
                .add_lambda_integrations(apigw_spec["route"])
            )

        # get lambda layer reference
        layer_dict = {}
        if ref_layer_dict is not None:
            for layer_id, layer_arn_or_name in ref_layer_dict.items():
                layer_version_arn = self._resolve_lambda_layer_arn(layer_arn_or_name)
                layer_dict[layer_id] = LayerVersion.from_layer_version_arn(
                    self,
                    layer_version_arn,
                    layer_version_arn=layer_version_arn,
                )

        # create repository (for each batch_func)
        if batch_spec_dict is not None:
            for batch_func_name in batch_spec_dict.keys():
                ECRCreator(self, "{}-{}".format(api_name, batch_func_name))

        # for each stage

        for stage_spec in stage_spec_dict.values():
            branch_name = stage_spec["branch"]
            # env for lambda
            env_dict = {
                self.ENV_BRANCH_KEY: branch_name,
                self.ENV_API_KEY: api_name,
            }
            if "bucket" in stage_spec:
                env_dict[self.ENV_BUCKET_KEY] = stage_spec["bucket"]

            # create queues (for each stage and each sqs_for_lambda)
            lambda_to_queue = {}
            if sqs_spec_dict is not None:
                for lambda_func_name, sqs_spec in sqs_spec_dict.items():
                    additional_timeout = sqs_spec.get("additional_timeout", 10)
                    lambda_spec = lambda_spec_dict[lambda_func_name]
                    base_timeout = lambda_spec.get("timeout", 3)

                    queue_prefix = "{}-{}-{}".format(
                        api_name, branch_name, lambda_func_name
                    )
                    sqs_creator = SQSCreator(
                        self,
                        queue_prefix + "_waiting",
                        queue_prefix + "_dead",
                        visibility_timeout_sec=base_timeout + additional_timeout,
                    )
                    lambda_to_queue[lambda_func_name] = sqs_creator.queue

            # create lambdas (for each stage and each lambda_func)
            lambda_to_func = {}
            if lambda_spec_dict is not None:
                for lambda_func_name, lambda_spec in lambda_spec_dict.items():
                    lambda_name = "{}-{}-{}".format(
                        api_name, branch_name, lambda_func_name
                    )
                    additional_env_dict = (
                        {
                            self.ENV_NEXT_SQS_KEY: "{}-{}-{}_waiting".format(
                                api_name, branch_name, lambda_spec["queue_next"]
                            )
                        }
                        if "queue_next" in lambda_spec
                        else {}
                    )

                    layers = (
                        [layer_dict[layer_id] for layer_id in lambda_spec["layer_list"]]
                        if "layer_list" in lambda_spec
                        else None
                    )

                    lambda_creator = LambdaCreator(
                        self,
                        lambda_name,
                        code=(
                            Code.from_asset(
                                self._resolve_path(lambda_spec["code"], root_path)
                            )
                            if "code" in lambda_spec
                            else None
                        ),
                        layers=layers,
                        env_dict={**env_dict, **additional_env_dict},
                        test_schema_path=(
                            self._resolve_path(lambda_spec.get("test"), root_path)
                            if "test" in lambda_spec
                            else None
                        ),
                        timeout=lambda_spec.get("timeout"),
                        memory_size=lambda_spec.get("memory_size"),
                        storage_size=lambda_spec.get("storage_size"),
                    )
                    if lambda_func_name in apigw_spec["route"]:
                        lambda_creator.called_by_apigateway(api_creator.api)
                    if lambda_func_name in lambda_to_queue:
                        lambda_creator.called_by_sqs(lambda_to_queue[lambda_func_name])
                    lambda_to_func[lambda_func_name] = lambda_creator.func

            # create batchs (for each stage and each batch_func)
            if ref_vpc is not None and batch_spec_dict is not None:
                for batch_func_name, batch_spec in batch_spec_dict.items():
                    BatchCreator(
                        self,
                        "{}-{}-{}".format(api_name, branch_name, batch_func_name),
                        "{}.dkr.ecr.{}.amazonaws.com/{}-{}:{}".format(
                            self.account,
                            self.region,
                            api_name,
                            batch_func_name,
                            branch_name,
                        ),
                        batch_spec["maxv_cpus"],
                        ref_vpc["subnet_id_list"],
                        ref_vpc["security_group_id"],
                        queue_state_lambda=lambda_to_func[
                            batch_spec.get("queue_state_lambda")
                        ],
                        env_dict=env_dict,
                        memory=batch_spec.get("memory"),
                        vcpu=batch_spec.get("vcpu"),
                    )

    def create_from_json(
        self,
        json_path,
        *,
        schema_path: str | None = None,
    ):
        """
        jsonによるAPI定義に従ってAWS上のリソースを構築します
        jsonファイル中の下記は文字列置換されます
        - {$account}: AWSアカウント名で置換します
        - {$api}: jsonファイル中で定義するnameで置換します
        """

        with open(json_path) as f:
            text = f.read()
            raw_api_spec: str = json.loads(text)

            replaced_text = (
                text.replace("{$api}", raw_api_spec["name"])
                .replace("{$account}", self.account)
                .replace("{$region}", self.region)
            )
            api_spec: str = json.loads(replaced_text)

        self.create(
            api_spec, root_path=os.path.dirname(json_path), schema_path=schema_path
        )
