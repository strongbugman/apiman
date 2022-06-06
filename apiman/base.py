import copy
import json
import os
import typing
from collections import OrderedDict

import jsonschema_rs
import xmltodict
import yaml

import apiman


class Apiman:
    HTTP_METHODS = {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "connect",
        "options",
        "trace",
    }
    SPECIFICATION_FILE = "__spec_file__"
    SPECIFICATION_YAML = "__spec_yaml__"
    SPECIFICATION_DICT = "__spec_dict__"
    STATIC_DIR = f"{getattr(apiman, '__path__')[0]}/static/"
    VALIDATE_REQUEST_CONTENT_TYPES = {
        "json": ("application/json",),
        "xml": ("application/xml",),
        "form": ("application/x-www-form-urlencoded", "multipart/form-data"),
    }

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
        self._path_schemas: typing.Dict[
            str, typing.Dict[str, typing.Any]
        ] = {}  # {"{path}_{method}": {schema}}

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

    def _load_specification(self) -> typing.Dict:
        if not self.loaded:
            # self.specification = self.expand_specification(self.specification)
            self.loaded = True
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

    def expand_specification(self, obj: typing.Any) -> typing.Any:
        if isinstance(obj, dict) and "$ref" in obj:
            return self.get_by_ref(obj["$ref"])
        else:
            if isinstance(obj, list):
                for i, o in enumerate(obj):
                    obj[i] = self.expand_specification(o)
            elif isinstance(obj, dict):
                for i, o in obj.items():
                    obj[i] = self.expand_specification(o)
            return obj

    def validate_specification(self, schema_path=""):
        if not schema_path:
            if self.version[0] > 2:
                schema_path = os.path.join(self.STATIC_DIR, "openapi3.1_schema.yaml")
            else:
                schema_path = os.path.join(self.STATIC_DIR, "openapi2_schema.json")

        jsonschema_rs.JSONSchema(self.load_file(schema_path)).validate(
            self.specification
        )

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

    def _get_path_schema(self, path: str, method: str):
        cache_key = f"{path}_{method}"
        if cache_key in self._path_schemas:
            return self._path_schemas[cache_key]

        schema: typing.Dict[str, typing.Dict[str, typing.Any]] = {
            "query": {},
            "header": {},
            "path": {},
            "cookie": {},
            "json": {},
            "xml": {},
            "form": {},
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
        form_schema = copy.deepcopy(base_schema)
        for d in self.specification["paths"][path][method].get("parameters", []):
            d = self.expand_specification(d)
            if d.get("in") == "query":
                _schema = query_schema
            elif d.get("in") == "header":
                _schema = header_schema
            elif d.get("in") == "path":
                _schema = path_schema
            elif d.get("in") == "cookie":
                _schema = cookie_schema
            elif d.get("in") == "formData":
                _schema = form_schema
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
            ("form", form_schema),
        ):
            if s["properties"]:
                schema[k] = s
        # request body
        if self.version[0] > 2:
            for k, ts in self.VALIDATE_REQUEST_CONTENT_TYPES.items():
                for t in ts:
                    try:
                        d = self.specification["paths"][path][method]["requestBody"][
                            "content"
                        ][t]
                        d = self.expand_specification(d)
                        schema[k] = d["schema"]
                    except KeyError:
                        pass
        self._path_schemas[cache_key] = schema
        return schema

    def get_request_data(self, request: typing.Any, k: str) -> typing.Any:
        pass

    async def async_get_request_data(self, request: typing.Any, k: str) -> typing.Any:
        return self.get_request_data(request, k)

    def get_request_schema(self, request: typing.Any) -> typing.Dict:
        pass

    def get_request_content_type(self, request: typing.Any) -> str:
        return request.headers.get("Content-Type", "") or request.headers.get(
            "content-type", ""
        )

    def iter_request_schema(
        self, request: typing.Any, ignore: typing.Sequence[str] = tuple()
    ) -> typing.Generator[typing.Tuple[str, typing.Dict], None, None]:
        _ignore = set(ignore)
        schema = self.get_request_schema(request)
        body_schema_count = body_miss_count = 0
        for k, s in schema.items():
            if not s or k in _ignore:
                continue
            if k in self.VALIDATE_REQUEST_CONTENT_TYPES:
                body_schema_count += 1
                if (
                    self.get_request_content_type(request).split(";")[0]
                    not in self.VALIDATE_REQUEST_CONTENT_TYPES[k]
                ):
                    body_miss_count += 1
                    continue
            yield k, s
        if body_schema_count and body_schema_count == body_miss_count:
            raise jsonschema_rs.ValidationError(
                "Miss body content", "Miss body content", [], []
            )

    def validate_request(
        self, request: typing.Any, ignore: typing.Sequence[str] = tuple()
    ):
        for k, s in self.iter_request_schema(request, ignore=ignore):
            data = self.get_request_data(request, k)
            jsonschema_rs.JSONSchema(s).validate(data)

    async def async_validate_request(
        self, request: typing.Any, ignore: typing.Sequence[str] = tuple()
    ):
        for k, s in self.iter_request_schema(request, ignore=ignore):
            data = await self.async_get_request_data(request, k)
            jsonschema_rs.JSONSchema(s).validate(data)

    def from_file(self, file_path: str) -> typing.Callable:
        def decorator(func: typing.Callable) -> typing.Callable:
            setattr(func, self.SPECIFICATION_FILE, file_path)
            return func

        return decorator

    def from_yaml(self, content: str) -> typing.Callable:
        def decorator(func: typing.Callable) -> typing.Callable:
            setattr(func, self.SPECIFICATION_YAML, content)
            return func

        return decorator

    def from_dict(self, content: typing.Dict) -> typing.Callable:
        def decorator(func: typing.Callable) -> typing.Callable:
            setattr(func, self.SPECIFICATION_DICT, content)
            return func

        return decorator

    def parse(self, func: typing.Callable) -> typing.Dict[str, typing.Any]:
        specification = {}
        if func.__doc__:
            specification = yaml.safe_load(func.__doc__.split("---")[-1])
            if not isinstance(specification, dict):
                specification = {}
        if specification:
            return specification
        elif hasattr(func, self.SPECIFICATION_YAML):
            return yaml.safe_load(getattr(func, self.SPECIFICATION_YAML))
        elif hasattr(func, self.SPECIFICATION_DICT):
            return getattr(func, self.SPECIFICATION_DICT)
        elif hasattr(func, self.SPECIFICATION_FILE):
            return self.load_file(getattr(func, self.SPECIFICATION_FILE))
        else:
            return specification

    def generate_specification_file(self, filename: str):
        with open(filename, "w") as f:
            f.writelines(
                json.dumps(self.specification)
                if filename.endswith("json")
                else yaml.safe_dump(self.specification)
            )

    @staticmethod
    def load_file(file_path: str) -> typing.Dict:
        with open(file_path) as f:
            if file_path.endswith("json"):
                return json.load(f)
            else:
                return yaml.safe_load(f)

    @staticmethod
    def xmltodict(content: typing.Union[str, bytes]):
        data = xmltodict.parse(content)

        for k in list(data.keys()):
            data = dict(data[k]) if isinstance(data[k], OrderedDict) else data[k]
            break
        return data
