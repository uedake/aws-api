import json
import os

import boto3


class SqsAccess:
    def __init__(
        self, queue_name: str, account: str | None = None, region: str | None = None
    ):

        self.endpoint_url = "https://sqs.{}.amazonaws.com".format(
            region if region is not None else os.environ["AWS_REGION"]
        )
        self.queue_url = "{}/{}/{}".format(
            self.endpoint_url,
            (
                account
                if account is not None
                else boto3.client("sts").get_caller_identity()["Account"]
            ),
            queue_name,
        )
        self.client = boto3.client("sqs", endpoint_url=self.endpoint_url)

    def send_json_message(self, message_dict: dict) -> dict:
        return self.client.send_message(
            QueueUrl=self.queue_url, MessageBody=json.dumps(message_dict)
        )


def lambda_handler(event, context):
    print("sample lambda function called!")
    output_dict = {
        "Records": event.get("Records"),
        "queryStringParameters": event.get("queryStringParameters"),
        "pathParameters": event.get("pathParameters"),
        "body": event.get("body"),
    }
    print(output_dict)

    SqsAccess(os.environ["NextSQS"]).send_json_message(output_dict)

    return {"statusCode": 200, "body": json.dumps(output_dict)}
