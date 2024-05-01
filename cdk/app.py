#!/usr/bin/env python3
import os

import aws_cdk as cdk

from src_cdk.stack import APIStack

app = cdk.App()
APIStack(
    app,
    "SampleAPI",
    env={
        "account": os.environ["CDK_DEFAULT_ACCOUNT"],
        "region": os.environ["CDK_DEFAULT_REGION"],
    },
).create_sample()

app.synth()
