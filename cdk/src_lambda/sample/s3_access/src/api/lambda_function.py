import json
import os

from common.aws_util import (
    ApiGatewayEventAnalyzer,
    WebApiException,
    ErrorCode,
    S3Access,
)

_param_spec = {
    "x": {
        "where": "body",
        "required": False,
        "default": 0,
    },
    "y": {
        "where": "query",
        "required": False,
        "default": 0,
        "options": {
            "convert_to_float": True,
        },
    },
    "z": {
        "where": "path",
        "required": False,
        "default": 0,
        "options": {
            "convert_to_float": True,
        },
    },
    "s3PathRead": {
        "where": "query",
        "required": False,
    },
}


def lambda_handler(event, context):
    try:
        api = ApiGatewayEventAnalyzer(event)
        params = api.solve_params(_param_spec)
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
            "x": params["x"],
            "y": params["y"],
            "z": params["z"],
            "s3PathRead": s3_path_read,
            "downloaded_content": downloaded_content,
            "sum": params["x"] + params["y"] + params["z"],
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
