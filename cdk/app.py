#!/usr/bin/env python3
import os

import aws_cdk as cdk

from src_cdk.api_stack import APIStack

app = cdk.App()
api_spec = app.node.try_get_context("api_spec")
schema = app.node.try_get_context("schema")
if api_spec is None:
    print("please set api_spec")
    print("cdk deploy --context api_spec=<path_to_api_spec_json> --context schema=<path_to_json_schema>")
    exit(1)

if schema is None:
    print("please set schema")
    print("cdk deploy --context api_spec=<path_to_api_spec_json> --context schema=<path_to_json_schema>")
    exit(1)


APIStack(
    app,
    "SampleAPI",
    env={
        "account": os.environ["CDK_DEFAULT_ACCOUNT"],
        "region": os.environ["CDK_DEFAULT_REGION"],
    },
).create_from_json(api_spec,schema_path=schema)

app.synth()
