import aws_cdk as cdk
from aws_cdk import Duration, Stack

from aws_cdk.aws_ecr import LifecycleRule, Repository, TagStatus


class ECRCreator:
    def __init__(
        self,
        scope: Stack,
        repository_name: str,
    ):
        self.scope = scope
        Repository(
            self.scope,
            "{}-ecr".format(repository_name),
            repository_name=repository_name,
            image_scan_on_push=False,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            lifecycle_rules=[
                LifecycleRule(
                    max_image_age=Duration.days(7),
                    tag_status=TagStatus.UNTAGGED,
                ),
            ],
        )
