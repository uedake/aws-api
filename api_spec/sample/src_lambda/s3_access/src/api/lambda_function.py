import json
import os

from ..awsutil.aws_util import (
    ApiGatewayEventAnalyzer,
    WebApiException,
    ErrorCode,
    S3Access,
)

_param_spec = {
    "msg": {
        "where": "query",
        "required": False,
    },
    "s3PathRead": {
        "where": "query",
        "required": False,
    },
    "data": {
        "where": "body",
        "required": False,
    },
}


def lambda_handler(event, context):
    try:
        api = ApiGatewayEventAnalyzer(event)
        params = api.solve_http_params(_param_spec)
        print("params:")
        print(params)

        bucket = os.environ.get("Bucket")
        s3_path_read = params["s3PathRead"]
        downloaded_content = None
        if s3_path_read is not None and bucket is not None:
            s3 = S3Access(bucket, s3_path_read)
            try:
                s3.download_file("/tmp/setting.json")
                with open("/tmp/setting.json") as f:
                    downloaded_content = f.read()

            except Exception:
                downloaded_content = None

        outputDict = {
            "msg": params["msg"],
            "data": params["data"],
            "s3PathRead": s3_path_read,
            "downloaded_content": downloaded_content,
        }

        if bucket is not None:

            with open(os.path.join(os.path.dirname(__file__), "template.html")) as f:
                template = f.read()
            html = template.replace("{$output}", json.dumps(outputDict))

            with open("/tmp/index.html", mode="w") as f:
                f.write(html)
            s3 = S3Access(bucket)
            s3.upload_one("/tmp/index.html",content_type="text/html")

        return {"statusCode": 200, "body": json.dumps(outputDict)}
    except WebApiException as webex:
        return webex.create_error_response()
    except Exception as ex:
        webex = WebApiException(500, ErrorCode.ServerLogicError, str(ex))
        raise webex
