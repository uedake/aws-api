import os
import traceback

from fastapi import FastAPI
from pydantic import BaseModel
from mangum import Mangum

try:
    import numpy as np
except Exception:
    print("[WARN] numpy not found")

DEBUG_MODE = True
app = FastAPI()


class Request(BaseModel):
    val: float | None = None


class Response(BaseModel):
    path_val: float | None
    query_val: float | None
    body_val: float | None
    avg: float | None


class Error(BaseModel):
    msg: str
    tb: list[str]


@app.get("/numpy", response_model=Response | Error)
@app.get("/numpy/{path_val}", response_model=Response | Error)
def calc_average(val: float | None = None, path_val: float | None = None):
    try:
        vec = np.array([v for v in [val, path_val] if v is not None])
        avg = float(np.average(vec)) if len(vec) > 0 else None
        return Response(path_val=path_val, query_val=val, body_val=None, avg=avg)
    except Exception as ex:
        if DEBUG_MODE:
            return Error(
                msg="Exception in Lambda",
                tb=traceback.format_exc().split("\n"),
            )
        else:
            raise ex


@app.post("/numpy", response_model=Response | Error)
@app.post("/numpy/{path_val}", response_model=Response | Error)
def calc_average(
    val: float | None = None,
    req: Request | None = None,
    path_val: float | None = None,
):
    try:
        body_val = req.val if req is not None else None

        vec = np.array([v for v in [val, body_val, path_val] if v is not None])
        avg = float(np.average(vec)) if len(vec) > 0 else None
        return Response(
            path_val=path_val,
            query_val=val,
            body_val=body_val,
            avg=avg,
        )
    except Exception as ex:
        if DEBUG_MODE:
            return Error(
                msg="Exception in Lambda",
                tb=traceback.format_exc().split("\n"),
            )
        else:
            raise ex


ENV_BRANCH_KEY = "Branch"
branch = os.environ.get(ENV_BRANCH_KEY)
if branch is None or branch == "main":
    lambda_handler = Mangum(app)
else:
    lambda_handler = Mangum(app, api_gateway_base_path=f"/{branch}")
