from __future__ import annotations

from aws_cdk import Stack
from aws_cdk.aws_sns import Topic
from aws_cdk.aws_iam import PolicyStatement


class SNSCreator:
    def __init__(
        self,
        scope: Stack,
        topic_name: str,
        description: str,
    ) -> None:
        self.scope = scope
        self.topic = Topic(
            self.scope, topic_name, topic_name=topic_name, display_name=description
        )

    def called_by_event_bridge(self) -> SNSCreator:
        self.topic.add_to_resource_policy(
            PolicyStatement.from_json(
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "events.amazonaws.com"},
                    "Action": "sns:Publish",
                    "Resource": self.topic.topic_arn,
                }
            )
        )
        return self
