from common.aws_util import WebApiException, ErrorCode


def lambda_handler(event, context):
    print("initial lambda function called!")

    ex = WebApiException(
        503,
        ErrorCode.ServerCodeNotProvided,
        "レポジトリからサーバにコードをまだデプロイできていないようです",
    )
    return ex.create_error_response()
