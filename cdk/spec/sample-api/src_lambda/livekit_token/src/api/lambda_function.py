import os
import traceback

from fastapi import FastAPI
from pydantic import BaseModel
from mangum import Mangum

try:
    from .util.livekit_util import LiveKitManager
except Exception:
    print("[WARN] import error")


ENV_BRANCH_KEY = "Branch"
ENV_SERVICE_KEY = "Service"
DEBUG_MODE = True
app = FastAPI()
branch = os.environ.get(ENV_BRANCH_KEY, "main")


class Response(BaseModel):
    token: str


class Error(BaseModel):
    msg: str
    tb: list[str]


@app.get("/livekit_token", response_model=Response | Error)
def create_token(room_name: str, identity: str, username: str):
    try:
        lk = LiveKitManager(livekit_server_type=branch)
        token = lk.create_token(
            identity,
            username,
            room_name,
        )
        print(f"token for")
        print(f"  identity={identity}")
        print(f"  name={username}")
        print(f"  room={room_name}")
        print("")
        print(token)
        return Response(token=token)
    except Exception as ex:
        if DEBUG_MODE:
            return Error(
                msg="Exception in Lambda",
                tb=traceback.format_exc().split("\n"),
            )
        else:
            raise ex


if branch == "main":
    lambda_handler = Mangum(app)
else:
    lambda_handler = Mangum(app, api_gateway_base_path=f"/{branch}")
