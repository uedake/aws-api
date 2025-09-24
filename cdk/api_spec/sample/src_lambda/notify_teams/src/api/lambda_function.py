import json
import urllib.request
import os

def lambda_handler(event, context):
    webhook_url = os.environ["NotificationUrl"]

    for record in event["Records"]:
        print("------received record")
        print(record)
        print("------")
        message = record["Sns"]["Message"]

        if isinstance(message, dict) and "source" in message:
            if message["source"] == "aws.amplify":
                body = handle_amplify_message(message, message["detail-type"])
            else:
                body = handle_other_message(message, record["Sns"]["Subject"])
        else:
            body = handle_other_message(message, record["Sns"]["Subject"])

        teams_message = {
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": body,
                    },
                }
            ]
        }

        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(teams_message).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as response:
                resp_body = response.read().decode("utf-8")
                print("response received")
                print(resp_body)
        except urllib.error.HTTPError as e:
            print(f"❌ HTTPError: {e.code} - {e.reason}")
            print("レスポンス本文:", e.read().decode("utf-8"))
        except urllib.error.URLError as e:
            print(f"❌ URLError: {e.reason}")
        except Exception as e:
            print(f"❌ その他のエラー: {str(e)}")

    return {"status": "done"}


def handle_other_message(message: str | dict, subject: str | None = None):
    return [
        {
            "type": "TextBlock",
            "text": subject,
            "weight": "Bolder",
            "size": "Large",
            "color": "Accent",
        },
        {
            "type": "TextBlock",
            "text": json.dumps(message),
            "wrap": True,
        },
    ]


def handle_amplify_message(message_dict: dict, subject: str | None = None):
    msg = [
        {
            "type": "TextBlock",
            "text": subject,
            "weight": "Bolder",
            "size": "Large",
            "color": "Accent",
        }
    ]

    status2msg = {
        "STARTED": "開始しました",
        "SUCCEED": "✅ 成功しました",
        "FAILED": "失敗しました",
    }

    status = message_dict["detail"]["jobStatus"]
    if status in status2msg.keys():
        msg += [
            {
                "type": "TextBlock",
                "text": "Webアプリ（{}）のデプロイが{}".format(
                    message_dict["detail"]["appId"],
                    status2msg[status],
                ),
                "wrap": True,
            },
            {
                "type": "FactSet",
                "facts": [
                    {
                        "title": "branchName",
                        "value": message_dict["detail"]["branchName"],
                    },
                    {
                        "title": "jobId",
                        "value": message_dict["detail"]["jobId"],
                    },
                ],
            },
        ]
    else:
        msg += [
            {
                "type": "TextBlock",
                "text": json.dumps(message_dict["detail"]),
                "wrap": True,
            }
        ]
    return msg
