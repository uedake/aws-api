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
                    "Sid": "__default_statement_ID",
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": [
                        "SNS:GetTopicAttributes",
                        "SNS:SetTopicAttributes",
                        "SNS:AddPermission",
                        "SNS:RemovePermission",
                        "SNS:DeleteTopic",
                        "SNS:Subscribe",
                        "SNS:ListSubscriptionsByTopic",
                        "SNS:Publish",
                    ],
                    "Resource": "arn:aws:sns:ap-northeast-1:821721610090:RemoteMonitoringCICD",
                    "Condition": {"StringEquals": {"AWS:SourceOwner": "821721610090"}},
                }
            )
        )
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
