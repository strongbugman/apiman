import copy
import json
import os
import typing

import jsonschema_rs
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
        template=os.path.join(STATIC_DIR, "template.yaml"),
    ):
        self.title = title
        self.specification_url = specification_url
        self.swagger_url = swagger_url
        self.redoc_url = redoc_url
        self.swagger_template = swagger_template
        self.redoc_template = redoc_template
        self.specification = self.load_file(template)
        self.loaded = False

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
    def version(self) -> typing.Tuple[int, ...]:
        _version = self.specification.get("swagger") or self.specification.get(
            "openapi"
        )
        assert _version, "Wrong API specification format"
        return tuple(map(int, _version.split(".")))

    def load_specification(self, app: typing.Any) -> typing.Dict:
        self.specification = self.expande(self.specification)
        return self.specification

    def get_by_ref(self, ref: str) -> typing.Any:
        data = self.specification
        for k in ref.split("/"):
            if k == "#":
                continue
            elif k not in data:
                raise ValueError(f"Wrong ref: {ref}")
            data = data[k]

        return data

    def expande(self, obj: typing.Any) -> typing.Any:
        if isinstance(obj, dict) and "$ref" in obj:
            return self.get_by_ref(obj["$ref"])
        else:
            if isinstance(obj, list):
                for i, o in enumerate(obj):
                    obj[i] = self.expande(o)
            elif isinstance(obj, dict):
                for i, o in obj.items():
                    obj[i] = self.expande(o)
            return obj

    def add_schema(self, name: str, definition: typing.Dict[str, typing.Any]):
        if self.version[0] > 2:
            if "components" not in self.specification:
                self.specification["components"] = {}
            if "schemas" not in self.specification["components"]:
                self.specification["components"]["schemas"] = {}
            self.specification["components"]["schemas"][name] = definition
        else:
            if "definitions" not in self.specification:
                self.specification["definitions"] = {}
            self.specification["definitions"][name] = definition

    def add_path(
        self, path: str, specification: typing.Dict, method: typing.Optional[str] = None
    ):
        if "paths" not in self.specification:
            self.specification["paths"] = {}
        if path not in self.specification["paths"]:
            self.specification["paths"][path] = {}

        if method:
            self.specification["paths"][path][method.lower()] = specification
        else:
            self.specification["paths"][path] = specification

    def get_path(self, path: str, method: str):
        schema: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "query": {},
            "json": {},
            "header": {},
            "path": {},
            "cookie": {},
        }
        if (
            "paths" not in self.specification
            or path not in self.specification["paths"]
            or method not in self.specification["paths"][path]
        ):
            return schema
        # parameters
        base_schema: typing.Dict[str, typing.Any] = {
            "type": "object",
            "properties": {},
            "required": [],
        }
        query_schema = copy.deepcopy(base_schema)
        header_schema = copy.deepcopy(base_schema)
        path_schema = copy.deepcopy(base_schema)
        cookie_schema = copy.deepcopy(base_schema)
        for d in self.specification["paths"][path][method].get("parameters", []):
            if d.get("in") == "query":
                _schema = query_schema
            elif d.get("in") == "header":
                _schema = header_schema
            elif d.get("in") == "path":
                _schema = path_schema
            elif d.get("in") == "cookie":
                _schema = cookie_schema
            elif self.version[0] <= 2 and d.get("in") == "body" and "schema" in d:
                schema["json"] = d["schema"]
                continue
            else:
                continue
            if self.version[0] > 2:
                if "schema" not in d:
                    continue
                _schema["properties"][d["name"]] = d["schema"]
            else:
                if "type" not in d:
                    continue
                _schema["properties"][d["name"]] = {"type": d["type"]}
            if d.get("required", False):
                _schema["required"].append(d["name"])
        for k, s in (
            ("query", query_schema),
            ("header", header_schema),
            ("path", path_schema),
            ("cookie", cookie_schema),
        ):
            if s["properties"]:
                schema[k] = s
        # json body
        if self.version[0] > 2:
            try:
                d = self.specification["paths"][path][method]["requestBody"]["content"][
                    "application/json"
                ]
                schema["json"] = d["schema"]
            except KeyError:
                pass

        return schema

    def _get_request_data(self, request: typing.Any, k: str) -> typing.Dict:
        pass

    def _get_request_schema(self, request: typing.Any) -> typing.Dict:
        pass

    def validate_request(self, request: typing.Any):
        schema = self._get_request_schema(request)
        for k, s in schema.items():
            if not s:
                continue
            jsonschema_rs.JSONSchema(s).validate(self._get_request_data(request, k))

    def from_file(self, file_path: str) -> typing.Callable:
        def decorator(func: typing.Callable) -> typing.Callable:
            setattr(func, self.SPECIFICATION_FILE, file_path)
            return func

        return decorator

    def parse(self, func: typing.Callable) -> typing.Dict[str, typing.Any]:
        # doc-string
        specification = {}
        if func.__doc__:
            specification = yaml.safe_load(func.__doc__.split("---")[-1])
            if not isinstance(specification, dict):
                specification = {}
        # file
        if not specification and hasattr(func, self.SPECIFICATION_FILE):
            specification = self.load_file(getattr(func, self.SPECIFICATION_FILE))
        return specification

    @staticmethod
    def load_file(file_path: str) -> typing.Dict:
        with open(file_path) as f:
            if file_path.endswith("json"):
                return json.load(f)
            else:
                return yaml.safe_load(f)
