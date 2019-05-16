import typing
from collections import defaultdict
import json

import yaml
from yaml.scanner import ScannerError

import apiman


STATIC_DIR = f"{getattr(apiman, '__path__')[0]}/static/"


class OpenApi:
    SPECIFICATION_FILE = "__spec_file__"
    CONFIG = {
        "title": "OpenAPI Document",
        "specification_url": "/apiman/schema/",
        "swagger_url": "/apiman/swagger/",
        "redoc_url": "/apiman/redoc/",
        "swagger_template": f"{STATIC_DIR}swagger.html",
        "redoc_template": f"{STATIC_DIR}redoc.html",
    }

    def __init__(self, template=f"{STATIC_DIR}template.yml", **config):
        self.specification = self.load_file(template)
        self.config = self.CONFIG.copy()
        self.config.update(config)
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
    def is_swagger(self):
        return "swagger" in self.specification

    def add_schema(self, name: str, definition: typing.Dict):
        if self.is_swagger:
            self.specification["definitions"][name] = definition
        else:
            self.specification["components"]["schemas"][name] = definition

    def from_file(self, file_path: str) -> typing.Callable:
        def decorator(func: typing.Callable) -> typing.Callable:
            setattr(func, self.SPECIFICATION_FILE, file_path)
            return func

        return decorator

    def from_doc(self, func: typing.Callable) -> typing.Dict:
        if not func.__doc__:
            return {}

        try:
            spec = yaml.safe_load(func.__doc__.split("---")[-1])
        except ScannerError:
            return {}
        if not isinstance(spec, dict):
            return {}

        return spec

    def from_func(self, func: typing.Callable) -> typing.Dict:
        specification = self.from_doc(func)
        if not specification and hasattr(func, self.SPECIFICATION_FILE):
            specification = self.load_file(getattr(func, self.SPECIFICATION_FILE))
        return specification

    def _load_specification(self, path: str, method: str, specification: typing.Dict):
        schemas = specification.pop("definitions" if self.is_swagger else "schemas", {})
        for name, schema in schemas.items():
            self.add_schema(name, schema)

        self.specification["paths"][path][method.lower()] = specification

    @staticmethod
    def load_file(file_path: str) -> typing.Dict:
        with open(file_path) as f:
            if file_path.endswith("json"):
                return json.load(f)
            else:
                return yaml.safe_load(f)
