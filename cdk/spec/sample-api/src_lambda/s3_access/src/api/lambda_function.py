import json
import os
import traceback
import shutil

from awsutil.aws_util import (
    ApiGatewayEventAnalyzer,
    S3Access,
)

_param_spec = {
    "s3Key": {
        "where": "path",
        "required": True,
    }
}


def lambda_handler(event, context):
    try:
        api = ApiGatewayEventAnalyzer(event)
        params = api.solve_http_params(_param_spec)
        print("params:")
        print(params)

        bucket = os.environ.get("Bucket")
        s3_key = params["s3Key"]
        text_content = None
        if bucket is not None:
            shutil.rmtree(f"/tmp/{s3_key}", ignore_errors=True)
            s3 = S3Access(bucket, s3_key)
            try:
                s3.download_file(f"/tmp/{s3_key}")
                with open(f"/tmp/{s3_key}") as f:
                    text_content = f.read()
            except Exception:
                pass

        output_s3_key = "s3_access_log.html"
        outputDict = {
            "bucket": bucket,
            "input_s3_key": s3_key,
            "exist": os.path.exists(f"/tmp/{s3_key}"),
            "text_content": text_content,
            "output_s3_key": output_s3_key,
        }

        if bucket is not None:
            with open(os.path.join(os.path.dirname(__file__), "template.html")) as f:
                template = f.read()
            html = template.replace("{$output}", json.dumps(outputDict))

            with open(f"/tmp/{output_s3_key}", mode="w") as f:
                f.write(html)
            s3 = S3Access(bucket)
            s3.upload_one(f"/tmp/{output_s3_key}", content_type="text/html")

        return {"statusCode": 200, "body": json.dumps(outputDict)}
    except Exception as ex:
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "msg": "Exception in Lambda",
                    "tb": traceback.format_exc().split("\n"),
                }
            ),
        }
