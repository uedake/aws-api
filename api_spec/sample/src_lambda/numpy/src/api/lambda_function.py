import json
import numpy as np

from common.aws_util import (
    ApiGatewayEventAnalyzer,
    WebApiException,
    ErrorCode,
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
}


def lambda_handler(event, context):
    try:
        api = ApiGatewayEventAnalyzer(event)
        params = api.solve_http_params(_param_spec)
        print("params:")
        print(params)

        vec = np.array([params["x"], params["y"], params["z"]])

        outputDict = {"vec": list(vec), "norm": np.linalg.norm(vec)}

        return {"statusCode": 200, "body": json.dumps(outputDict)}
    except WebApiException as webex:
        return webex.create_error_response()
    except Exception as ex:
        webex = WebApiException(500, ErrorCode.ServerLogicError, str(ex))
        raise webex
