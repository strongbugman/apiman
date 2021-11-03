import json
import os
import typing
from collections import defaultdict

import yaml

import apiman


class OpenApi:
    HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
    SPECIFICATION_FILE = "__spec_file__"
    STATIC_DIR = f"{getattr(apiman, '__path__')[0]}/static/"

    def __init__(
        self,
        title="OpenAPI Document",
        specification_url="/apiman/specification/",
        swagger_url="/apiman/swagger/",
        redoc_url="/apiman/redoc/",
        swagger_template=os.path.join(STATIC_DIR, "swagger.html"),
        redoc_template=os.path.join(STATIC_DIR, "redoc.html"),
        template=os.path.join(STATIC_DIR, "template.yml"),
    ):
        self.title = title
        self.specification_url = specification_url
        self.swagger_url = swagger_url
        self.redoc_url = redoc_url
        self.swagger_template = swagger_template
        self.redoc_template = redoc_template
        self.specification = self.load_file(template)
        self.loaded = False

        if self.is_swagger:
            self.specification.setdefault("definitions", {})
        else:
            self.specification.setdefault("components", {"schemas": {}})
        paths = self.specification.pop("paths", {})
        self.specification["paths"] = defaultdict(dict)
        for k, v in paths.items():
            self.specification["paths"][k] = v

    @property
    def config(self) -> typing.Dict[str, str]:
        return {
            "title": self.title,
            "specification_url": self.specification_url,
            "swagger_url": self.swagger_url,
            "redoc_url": self.redoc_url,
            "swagger_template": self.swagger_template,
            "redoc_template": self.redoc_template,
        }

    @property
    def is_swagger(self) -> bool:
        return "swagger" in self.specification

    def add_schema(self, name: str, definition: typing.Dict[str, typing.Any]):
        if self.is_swagger:
            self.specification["definitions"][name] = definition
        else:
            self.specification["components"]["schemas"][name] = definition

    def from_file(self, file_path: str) -> typing.Callable:
        def decorator(func: typing.Callable) -> typing.Callable:
            setattr(func, self.SPECIFICATION_FILE, file_path)
            return func

        return decorator

    def from_doc(self, func: typing.Callable) -> typing.Dict[str, typing.Any]:
        if not func.__doc__:
            return {}

        spec = yaml.safe_load(func.__doc__.split("---")[-1])
        if not isinstance(spec, dict):
            return {}

        return spec

    def from_func(self, func: typing.Callable) -> typing.Dict[str, typing.Any]:
        specification = self.from_doc(func)
        if not specification and hasattr(func, self.SPECIFICATION_FILE):
            specification = self.load_file(getattr(func, self.SPECIFICATION_FILE))
        return specification

    def _load_specification(
        self, path: str, specification: typing.Dict, method: typing.Optional[str] = None
    ):
        if method:
            self.specification["paths"][path][method.lower()] = specification
        else:
            self.specification["paths"][path] = specification

    @staticmethod
    def load_file(file_path: str) -> typing.Dict:
        with open(file_path) as f:
            if file_path.endswith("json"):
                return json.load(f)
            else:
                return yaml.safe_load(f)
