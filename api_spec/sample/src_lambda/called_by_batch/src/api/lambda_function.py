import json

def lambda_handler(event, context):
    print("sample lambda function called!")
    if event["source"] != "aws.batch":
        raise ValueError(
            "Function only supports input from events with a source type of: aws.batch"
        )
    detail = event.get("detail")
    print("params:")
    print(detail)

    status = detail["status"]
    job_name = detail["jobName"]

    msg=f"バッチの状態が{status}に変化しました。{job_name}"
    print(text=msg)
    return {"statusCode": 200, "body": json.dumps(detail)}
