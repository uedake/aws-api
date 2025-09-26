import os
import sys
import importlib
from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


class OpenApiSchema:
    def __init__(self, spec: dict):
        self.spec = spec

    @staticmethod
    def from_yaml(path: str):
        with open(path) as f:
            spec = yaml.safe_load(f)
        return OpenApiSchema(spec)

    @staticmethod
    def from_fastapi_code(
        path: str, root_path: str | None = None, app_name: str = "app"
    ):
        if root_path is None:
            root_path = os.path.dirname(path)
            module_name = os.path.splitext(os.path.basename(path))[0]
        else:
            module_name = ".".join(Path(os.path.splitext(path)[0]).parts)
        return OpenApiSchema.from_fastapi_modeule(module_name, root_path, app_name)

    @staticmethod
    def from_fastapi_modeule(module_name: str, import_root: str, app_name: str = "app"):
        sys.path.append(os.path.abspath(import_root))
        print(os.path.abspath(import_root))
        mod = importlib.import_module(module_name)
        app: FastAPI = getattr(mod, app_name)

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        return OpenApiSchema(openapi_schema)

    def get_apigw_route(self):
        return [
            f"{method.upper()} {path}"
            for path, method_dict in self.spec["paths"].items()
            for method in method_dict
        ]
