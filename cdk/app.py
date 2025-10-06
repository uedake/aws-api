#!/usr/bin/env python3
import os
import json

import aws_cdk
from src_cdk.web_system_stack import WebSystemStack


def read_spec(spec_path: str, env: dict):
    """
    AWS上のリソースを構築する定義ファイルを読み込みます
    spec定義ファイル中の下記は文字列置換されます
    - {$account}: AWSアカウント名で置換します
    - {$region}: AWSリージョン名で置換します
    - {$service_name}: spec定義ファイルで定義するservice_nameで置換します
    """

    with open(spec_path) as f:
        text = f.read()
        raw_api_spec: str = json.loads(text)

        replaced_text = (
            text.replace("{$service_name}", raw_api_spec["service_name"])
            .replace("{$account}", env["account"])
            .replace("{$region}", env["region"])
        )
        return json.loads(replaced_text)


pwd = os.path.dirname(os.path.abspath(__file__))
env = {
    "account": os.environ["CDK_DEFAULT_ACCOUNT"],
    "region": os.environ["CDK_DEFAULT_REGION"],
}

app = aws_cdk.App()
spec_path = app.node.try_get_context("spec")
if spec_path is None:
    print("please set spec")
    print("cdk deploy --context spec=<path_to_spec_json>")
    exit(1)

spec_dict = read_spec(spec_path, env)

stack = WebSystemStack(
    app,
    f"{spec_dict["stack"]}",
    env=env,
)

stack.create(
    spec_dict,
    root_path=os.path.dirname(spec_path),
    schema_path=f"{pwd}/spec/schema.json",
    access_token=os.environ.get("GITHUB_PAT"),
)

app.synth()
