from __future__ import annotations

from aws_cdk import Stack
from aws_cdk.aws_batch import CfnComputeEnvironment, CfnJobDefinition, CfnJobQueue
from aws_cdk.aws_iam import ManagedPolicy, Role, ServicePrincipal
from aws_cdk.aws_logs import LogGroup
from aws_cdk.aws_lambda import Function
from aws_cdk.aws_events_targets import LambdaFunction
from aws_cdk.aws_events import EventPattern, Rule


class BatchCreator:

    def __init__(
        self,
        scope: Stack,
        batch_name: str,
        container_url: str,
        maxv_cpus: int,
        vpc_subnet_id_list: list[str],
        security_group_id: str,
        *,
        queue_state_lambda: Function | None = None,
        env_dict: dict | None = None,
        memory: int | None,
        vcpu: int | None,
    ):
        if len(vpc_subnet_id_list)==0:
            print(f"ignore creating {batch_name} because vpc_subnet_id_list is blank")
            return

        self.scope = scope
        self.batch_name = batch_name
        self.compute_env_name = "{}-ComputeEnvironment".format(self.batch_name)
        self.role_name_for_service = "{}-BatchServiceRole".format(self.batch_name)
        self.role_name_for_exe = "{}-ExecutionRole".format(self.batch_name)
        self.role_name_for_job = "{}-JobRole".format(self.batch_name)
        self.job_definition_name = "{}-JobDef".format(self.batch_name)
        self.job_queue_name = "{}-JobQueue".format(self.batch_name)
        self.rule_name = "{}-notice".format(self.job_queue_name)

        [service_role, execution_role, job_role] = self._create_roles()

        self._create_job_queue(
            maxv_cpus,
            vpc_subnet_id_list,
            security_group_id,
            service_role,
            queue_state_lambda=queue_state_lambda,
        )

        self._create_job_def(
            container_url,
            execution_role,
            job_role,
            env_dict=env_dict,
            memory=memory,
            vcpu=vcpu,
        )

    def _create_job_queue(
        self,
        maxv_cpus: int,
        vpc_subnet_id_list: list[str],
        security_group_id: str,
        service_role: Role,
        *,
        queue_state_lambda: Function | None = None,
    ) -> CfnJobQueue:

        compute_env = CfnComputeEnvironment(
            self.scope,
            self.compute_env_name,
            type="MANAGED",
            compute_environment_name=self.compute_env_name,
            service_role=service_role.role_arn,
            compute_resources=CfnComputeEnvironment.ComputeResourcesProperty(
                type="FARGATE",
                maxv_cpus=maxv_cpus,
                subnets=vpc_subnet_id_list,
                security_group_ids=[security_group_id],
            ),
        )
        queue = CfnJobQueue(
            self.scope,
            self.job_queue_name,
            compute_environment_order=[
                CfnJobQueue.ComputeEnvironmentOrderProperty(
                    compute_environment=compute_env.attr_compute_environment_arn,
                    order=1,
                )
            ],
            job_queue_name=self.job_queue_name,
            priority=1,
        )
        if queue_state_lambda is not None:
            Rule(
                self.scope,
                self.rule_name,
                rule_name=self.rule_name,
                event_pattern=EventPattern(
                    source=["aws.batch"],
                    detail_type=["Batch Job State Change"],
                    detail={
                        "status": ["RUNNING", "SUCCEEDED", "FAILED"],
                        "jobQueue": [queue.attr_job_queue_arn],
                    },
                ),
                targets=[LambdaFunction(queue_state_lambda)],
            )
        return queue

    def _create_job_def(
        self,
        container_url: str,
        execution_role: Role,
        job_role: Role,
        *,
        env_dict: dict | None = None,
        memory: int | None = None,
        vcpu: int | None = None,
    ) -> CfnJobDefinition:
        log_group_name = self.batch_name

        resource_requirements = []
        if memory is not None:
            resource_requirements.append(
                CfnJobDefinition.ResourceRequirementProperty(
                    type="MEMORY", value=str(memory)
                )
            )
        if vcpu is not None:
            resource_requirements.append(
                CfnJobDefinition.ResourceRequirementProperty(
                    type="VCPU", value=str(vcpu)
                )
            )

        LogGroup(
            self.scope, "{}-log".format(log_group_name), log_group_name=log_group_name
        )

        return CfnJobDefinition(
            self.scope,
            self.job_definition_name,
            job_definition_name=self.job_definition_name,
            type="container",
            platform_capabilities=["FARGATE"],
            container_properties=CfnJobDefinition.ContainerPropertiesProperty(
                image=container_url,
                environment=[
                    CfnJobDefinition.EnvironmentProperty(name=k, value=v)
                    for k, v in env_dict.items()
                ],
                execution_role_arn=execution_role.role_arn,
                job_role_arn=job_role.role_arn,
                log_configuration=CfnJobDefinition.LogConfigurationProperty(
                    log_driver="awslogs",
                    options={"awslogs-group": log_group_name},
                ),
                resource_requirements=resource_requirements,
            ),
        )

    def _create_roles(
        self,
    ) -> list:
        service_role = Role(
            self.scope,
            self.role_name_for_service,
            role_name=self.role_name_for_service,
            assumed_by=ServicePrincipal("batch.amazonaws.com"),
        )
        service_role.add_managed_policy(
            ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSBatchServiceRole"
            )
        )

        execution_role = Role(
            self.scope,
            self.role_name_for_exe,
            role_name=self.role_name_for_exe,
            assumed_by=ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        execution_role.add_managed_policy(
            ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AmazonECSTaskExecutionRolePolicy"
            )
        )

        job_role = Role(
            self.scope,
            self.role_name_for_job,
            role_name=self.role_name_for_job,
            assumed_by=ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        for name in [
            "service-role/AWSBatchServiceEventTargetRole",
            "service-role/AWSLambdaRole",
            "service-role/AWSLambdaSQSQueueExecutionRole",
            "AmazonS3FullAccess",
        ]:
            job_role.add_managed_policy(
                ManagedPolicy.from_aws_managed_policy_name(name)
            )

        return [service_role, execution_role, job_role]
