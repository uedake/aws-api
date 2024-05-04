import json

from common.aws_util import (
    ApiGatewayEventAnalyzer,
    WebApiException,
    ErrorCode,
    LambdaAccess,
)

_param_spec = {
    "x": {
        "where": "sqs",
        "required": False,
        "default": 0,
    },
    "y": {
        "where": "sqs",
        "required": False,
        "default": 0,
    },
    "z": {
        "where": "sqs",
        "required": False,
        "default": 0,
    },
}


def lambda_handler(event, context):
    try:
        api = ApiGatewayEventAnalyzer(event)
        params_list = api.solve_sqs_params_list(_param_spec)

        output_dict_list = []
        for params in params_list:
            print("params:")
            print(params)

            output_dict = {
                "x": params["x"],
                "y": params["y"],
                "z": params["z"],
                "sum": params["x"] + params["y"] + params["z"],
            }
            LambdaAccess.from_default("s3_access").invoke(
                body_dict={"data": output_dict},
                query_dict={"msg": "called by pipeline_process"},
            )

            output_dict_list.append(output_dict)
        print("output:")
        print(output_dict_list)

        return {"statusCode": 200, "body": json.dumps(output_dict_list)}
    except WebApiException as webex:
        return webex.create_error_response()
    except Exception as ex:
        webex = WebApiException(500, ErrorCode.ServerLogicError, str(ex))
        raise webex
