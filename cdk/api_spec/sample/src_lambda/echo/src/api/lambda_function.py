import json

def lambda_handler(event, context):
    print("sample lambda function called!")
    output_dict={
        "Records":event.get("Records"),
        "queryStringParameters":event.get("queryStringParameters"),
        "pathParameters":event.get("pathParameters"),
        "body":event.get("body")
    }
    print(output_dict)
    return {"statusCode": 200, "body": json.dumps(output_dict)}
