import json
import os

from aws_cdk import Stack
from aws_cdk.aws_lambda import Code

from constructs import Construct
from jsonschema import Draft202012Validator

from .lambda_creator import LambdaCreator
from .apigateway_creator import ApiGatewayCreator
from .sqs_creator import SQSCreator
from .ecr_creator import ECRCreator
from .batch_creator import BatchCreator
from .s3_creator import S3Creator



class APIStack(Stack):
    """
    下記をＡＷＳ上で作成します
    - lambda
    - batch (ecr含む)
    - apigw
    - sqs
    - s3

    これらのリソースは識別可能なように下記の部分名称を使って命名されます
    - api_name
      - api_spec["name"]で指定します
    - branch_name
      - api_spec["stage"]の中で指定します（複数指定可能）

    ■AWS lambdaの作成
    api_spec["lambda_func"]に従って、AWS lambdaを作成します
    - 下記名前のlambdaを作成します
      - "{api_name}-{branch_name}-{lambda_func_name}"
    {lambda_func_name}はapi_spec["lambda_func"]のkey名が使用されます

    lambdaを実行する前に別途上記lambdaにコードをアップロードしておいてください

    (補足) lambdaに設定される環境変数
    - Bucket
      - api_spec["stage"]中でステージごとに定義した値が設定されます
      - API全体に渡って共通のs3に各lambda中からアクセスする場合に、
        アクセス先のバケット名を指定しておくのに使用します
      - s3のバケットは別途自分で作成したものを参照することもできますし、
        このcdk中でapi_spec["s3"]を指定して作成することも可能です
    - Branch
      - branch_nameが設定されます
    - API
      - api_nameが設定されます
    - NextSQS
      - api_spec["lambda_func"]中でfuncごとに定義した値が設定されます
      - このlambdaの処理が終わった後に実行して欲しいSQSのキュー名を指定するのに使用します

    ■AWS batchとECRの作成
    api_spec["batch_func"]及びapi_spec["vpc_for_batch"]に従って、AWS batchとECRを作成します
    - 下記名前のECRレジストリを作成します
      - "{api_name}-{batch_func_name}"
    - 下記名前のtagを持つdockerイメージを実行するbatchを作成します
      - "{account}.dkr.ecr.{region}.amazonaws.com/{api_name}-{batch_func_name}:{branch_name}"
    {batch_func_name}はapi_spec["batch_func"]のkey名が使用されます

    このcdkではVPCを作成しません。cdk実行前に事前に別途VPCを作成しておく必要があります
    batchを実行する前に別途上記ECRレジストリに上記tag名でイメージをpushしておいてください

    ■API gatewayの作成
    api_spec["apigw"]に従って、lambdaを実行するためのAPI gatewayを作成します
    - 下記名前のAPI gatewayを作成します
      - "{api_name}"

    アクセス先のlambdaは、api_spec["lambda_func"]中で指定してください。

    ■SQSの作成
    api_spec["sqs_for_lambda"]に従ってlambdaを実行するためのSQSを作成します
    - 下記名前のSQSを作成します
      - "{api_name}-{branch_name}-{lambda_func_name}_waiting"
      - "{api_name}-{branch_name}-{lambda_func_name}_dead"
    {lambda_func_name}はapi_spec["sqs_for_lambda"]のkey名が使用されます

    アクセス先のlambdaは、api_spec["lambda_func"]中で指定してください。

    ■S3の作成
    api_spec["s3"]に従ってlambdaを実行するためのS3を作成します
    - 下記名前のS3を作成します
      - "{bucket_name}"
    {bucket_name}はapi_spec["s3"]のkey名が使用されます

    """

    ENV_BUCKET_KEY = "Bucket"
    ENV_BRANCH_KEY = "Branch"
    ENV_API_KEY = "API"
    ENV_NEXT_SQS_KEY = "NextSQS"

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

    def create(self, api_spec: dict):
        stage_spec_dict = (
            api_spec["stage"]
            if "stage" in api_spec
            else {
                "$default": {
                    "branch": "master",
                },
            }
        )

        # schema_check
        with open(os.path.join(os.path.dirname(__file__), "schema.json")) as f:
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
            vpc_spec=api_spec.get("vpc_for_batch"),
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
        vpc_spec: dict | None = None,
    ):
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

                    lambda_creator = LambdaCreator(
                        self,
                        lambda_name,
                        code=(
                            Code.from_asset(lambda_spec["code"])
                            if "code" in lambda_spec
                            else None
                        ),
                        env_dict={**env_dict, **additional_env_dict},
                        test_schema_path=lambda_spec.get("test"),
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
            if vpc_spec is not None and batch_spec_dict is not None:
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
                        vpc_spec["subnet_id_list"],
                        vpc_spec["security_group_id"],
                        queue_state_lambda=lambda_to_func[
                            batch_spec.get("queue_state_lambda")
                        ],
                        env_dict=env_dict,
                        memory=batch_spec.get("memory"),
                        vcpu=batch_spec.get("vcpu"),
                    )

    def create_from_json(self, json_path):
        """
        jsonによるAPI定義に従ってAWS上のリソースを構築します
        jsonファイル中の下記は文字列置換されます
        - {$account}: AWSアカウント名で置換します
        - {$api}: jsonファイル中で定義するnameで置換します
        """

        with open(json_path) as f:
            text = f.read()
            raw_api_spec: str = json.loads(text)

            replaced_text = text.replace("{$account}", self.account)
            replaced_text = replaced_text.replace("{$api}", raw_api_spec["name"])
            api_spec: str = json.loads(replaced_text)

        self.create(api_spec)

    def create_sample(self):
        """
        sample_api_spec.jsonから読み込んだapi_specを使用してAPIを構築します
        """

        json_path = os.path.join(
            os.path.dirname(__file__), "api_spec", "sample_api_spec.json"
        )

        self.create_from_json(json_path)
