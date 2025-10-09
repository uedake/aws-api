import json
import traceback
import os

import boto3

ENV_BRANCH_KEY = "Branch"
ENV_SERVICE_KEY = "Service"


def get_account():
    sts = boto3.client("sts")
    identity = sts.get_caller_identity()
    return identity["Account"]


def read_policy_json(
    json_path: str,
    region: str,
    accout: str,
    *,
    service_name: str | None = None,
    branch: str | None = None,
):
    """
    policy定義ファイル中の下記は文字列置換されます
    - {$account}: AWSアカウント名で置換します
    - {$region}: AWSリージョン名で置換します
    - {$service_name}: 引数で指定するservice_nameで置換します
    - {$branch}: 引数で指定するbranchで置換します
    """

    with open(json_path) as f:
        text = f.read()
        replaced_text = text.replace("{$account}", accout).replace("{$region}", region)
        if service_name is not None:
            replaced_text = replaced_text.replace("{$service_name}", service_name)
        if branch is not None:
            replaced_text = replaced_text.replace("{$branch}", branch)
        return replaced_text


def create_and_attach_iot_role(
    target: str,
    policy_json_path: str,
    *,
    service_name: str | None = None,
    branch: str | None = None,
):
    try:
        policy_json = read_policy_json(
            policy_json_path,
            os.environ["AWS_REGION"],
            get_account(),
            service_name=service_name,
            branch=branch,
        )
        policyName = f"{service_name}_{branch}"

        client = boto3.client("iot")
        try:
            client.get_policy(policyName=policyName)
        except client.exceptions.ResourceNotFoundException:
            client.create_policy(policyName=policyName, policyDocument=policy_json)

        client.attach_policy(policyName=policyName, target=target)
        return True
    except Exception as ex:
        print("Error on attaching policy")
        print(traceback.format_exc().split("\n"))
        return False


def lambda_handler(event, context):
    print("sample lambda function called!")
    query_param = event.get("queryStringParameters")
    print(query_param)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    success = create_and_attach_iot_role(
        query_param["cognitoIdentityId"],
        f"{script_dir}/iot_policy_template.json",
        service_name=os.environ[ENV_SERVICE_KEY],
        branch=os.environ[ENV_BRANCH_KEY],
    )
    output_dict = {"result": success}
    print(output_dict)
    return {"statusCode": 200, "body": json.dumps(output_dict)}
