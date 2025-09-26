import json
import os

import boto3


class LambdaAccess:
    def __init__(
        self, lambda_name: str, account: str | None = None, region: str | None = None
    ):
        self.client = boto3.client("lambda")
        self.func_arn = "arn:aws:lambda:{}:{}:function:{}".format(
            region if region is not None else os.environ["AWS_REGION"],
            (
                account
                if account is not None
                else boto3.client("sts").get_caller_identity()["Account"]
            ),
            lambda_name,
        )

    def invoke(self, *, body_dict: dict | None = None, query_dict: dict | None = None):
        payload = {}
        if body_dict is not None:
            payload["body"] = json.dumps(body_dict)
        if query_dict is not None:
            payload["queryStringParameters"] = query_dict

        response = self.client.invoke(
            FunctionName=self.func_arn,
            InvocationType="RequestResponse",
            LogType="Tail",
            Payload=json.dumps(payload),
        )

        return json.load(response["Payload"])


def lambda_handler(event, context):

    output_dict_list = []
    if "Records" in event:
        print("{} records received".format(len(event["Records"])))
        for record in event["Records"]:
            sqs_data = json.loads(record["body"])

            api_name = os.environ["API"]
            branch = os.environ["Branch"]
            LambdaAccess(f"{api_name}-{branch}-s3_access").invoke(
                body_dict={"data": sqs_data, "msg": "called by pipeline_process"},
            )

            output_dict_list.append(sqs_data)
        print("output:")
        print(output_dict_list)

    return {"statusCode": 200, "body": json.dumps(output_dict_list)}
