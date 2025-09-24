#!/usr/bin/env python3
import os
import json

import aws_cdk as cdk

from src_cdk.api_stack import APIStack

pwd = os.path.dirname(os.path.abspath(__file__))

app = cdk.App()
api_spec_path = app.node.try_get_context("api_spec")
schema_path = app.node.try_get_context("schema")
if api_spec_path is None:
    print("please set api_spec")
    print(
        "cdk deploy --context api_spec=<path_to_api_spec_json> --context schema=<path_to_json_schema>"
    )
    exit(1)

if schema_path is None:
    schema_path=f"{pwd}/api_spec/schema.json"

with open(api_spec_path) as f:
    api_spec = json.load(f)

APIStack(
    app,
    f"{api_spec["name"]}-stack",
    env={
        "account": os.environ["CDK_DEFAULT_ACCOUNT"],
        "region": os.environ["CDK_DEFAULT_REGION"],
    },
).create_from_json(api_spec_path, schema_path=schema_path)

app.synth()
