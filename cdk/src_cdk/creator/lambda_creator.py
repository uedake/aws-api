from __future__ import annotations

from aws_cdk import Duration, Size, Stack
from aws_cdk.aws_iam import ManagedPolicy, ServicePrincipal,Policy,Role
from aws_cdk.aws_lambda import Code, FileSystem, Function, Runtime
from aws_cdk.aws_eventschemas import CfnSchema
from aws_cdk.aws_lambda_event_sources import SqsEventSource, SnsEventSource
from aws_cdk.aws_sqs import Queue
from aws_cdk.aws_sns import Topic


class LambdaCreator:
    def __init__(
        self,
        scope: Stack,
        lambda_name: str,
        *,
        runtime: Runtime | None = None,
        managed_policy_list: list[str] | None = None,
        code: Code | None = None,
        handler: str | None = None,
        timeout: int | None = None,
        memory_size: int | None = None,
        storage_size: int | None = None,
        layers: list | None = None,
        env_dict: dict | None = None,
        efs_arn: str | None = None,
        efs_mount_path: str | None = "/mnt/efs",
        test_schema_path: str | None = None,
    ) -> None:
        self.scope = scope
        self.lambda_name = lambda_name

        self.func = self._create(
            lambda_name,
            runtime if runtime is not None else Runtime.PYTHON_3_12,
            managed_policy_list if managed_policy_list is not None else [],
            code if code is not None else Code.from_asset("initial_lambda"),
            handler=handler,
            timeout=timeout,
            memory_size=memory_size,
            storage_size=storage_size,
            layers=layers,
            env_dict=env_dict,
            filesystem=(
                FileSystem(arn=efs_arn, local_mount_path=efs_mount_path)
                if efs_arn is not None
                else None
            ),
            test_schema_path=test_schema_path,
        )

    def _create(
        self,
        lambda_name: str,
        runtime: Runtime,
        managed_policy_list: list[str],
        code: Code,
        *,
        handler: str | None = None,
        timeout: int | None = None,
        memory_size: int | None = None,
        storage_size: int | None = None,
        layers: list | None = None,
        env_dict: dict | None = None,
        filesystem: FileSystem | None = None,
        test_schema_path: str | None = None,
    ) -> Function:
        func = Function(
            self.scope,
            lambda_name,
            handler=handler,
            function_name=lambda_name,
            code=code,
            runtime=runtime,
            layers=layers,
            environment=env_dict,
            timeout=Duration.seconds(timeout) if timeout is not None else None,
            filesystem=filesystem,
            memory_size=memory_size,
            ephemeral_storage_size=(
                Size.mebibytes(storage_size) if storage_size else None
            ),
        )
        for name in managed_policy_list:
            func.role.add_managed_policy(
                ManagedPolicy.from_aws_managed_policy_name(name)
            )

        if test_schema_path is not None:
            with open(test_schema_path) as f:
                test_schema = f.read()

            CfnSchema(
                self.scope,
                f"{lambda_name}-schema",
                registry_name="lambda-testevent-schemas",
                type="OpenApi3",
                description="test event for lambda",
                schema_name=f"_{lambda_name}-schema",
                content=test_schema,
            )
        return func

    def called_by_apigateway(
        self,
        apigw_arn: str,
    ) -> LambdaCreator:
        """
        lambdaをAPI gatewayから呼び出せるようにします
        ※lambda側にリソースベースのポリシーを設定します。
        　リソースベースのポリシーで許可していれば、
        　呼び出し側のアイデンティティベースのポリシーで明示的に許可するのは不要
        """
        self.func.add_permission(
            "{}-permission".format(self.lambda_name),
            principal=ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=apigw_arn,
        )
        return self

    def called_by_sqs(
        self,
        queue: Queue,
    ) -> LambdaCreator:
        """
        lambdaをsqsから呼び出せるようにします
        ※lambda側にリソースベースのポリシーを設定します。
        　リソースベースのポリシーで許可していれば、
        　呼び出し側のアイデンティティベースのポリシーで明示的に許可するのは不要
        """
        self.func.add_event_source(SqsEventSource(queue, batch_size=1))
        return self

    def called_by_sns(
        self,
        topic: Topic,
    ) -> LambdaCreator:
        """
        lambdaをSNSから呼び出せるようにします
        ※lambda側にリソースベースのポリシーを設定します。
        　リソースベースのポリシーで許可していれば、
        　呼び出し側のアイデンティティベースのポリシーで明示的に許可するのは不要
        """
        self.func.add_event_source(SnsEventSource(topic))
        return self
