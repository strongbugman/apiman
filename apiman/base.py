import copy
import json
import os
import typing
from collections import OrderedDict
from email.message import Message

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
        "xml": ("application/xml", "text/xml"),
        "form": ("application/x-www-form-urlencoded", "multipart/form-data"),
    }
    OPENAPI2_PARAMETER_SCHEMA_KEYS = {
        "type",
        "format",
        "items",
        "collectionFormat",
        "default",
        "maximum",
        "exclusiveMaximum",
        "minimum",
        "exclusiveMinimum",
        "maxLength",
        "minLength",
        "pattern",
        "maxItems",
        "minItems",
        "uniqueItems",
        "enum",
        "multipleOf",
    }
    BODY_REQUIRED_KEY = "__body_required__"
    BODY_MEDIA_TYPES_KEY = "__body_media_types__"

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
        self._path_schemas: dict[
            str, dict[str, typing.Any]
        ] = {}  # {"{path}_{method}": {schema}}

    @property
    def config(self) -> dict[str, str]:
        return {
            "title": self.title,
            "specification_url": self.specification_url,
            "swagger_url": self.swagger_url,
            "redoc_url": self.redoc_url,
            "swagger_template": self.swagger_template,
            "redoc_template": self.redoc_template,
        }

    @property
    def version(self) -> tuple[int, ...]:
        _version = self.specification.get("swagger") or self.specification.get(
            "openapi"
        )
        assert _version, "Wrong API specification format"
        return tuple(map(int, _version.split(".")))

    def _load_specification(self) -> dict:
        if not self.loaded:
            self.loaded = True
        return self.specification

    def reset(self) -> None:
        """Mark collected routes and compiled validation schemas as stale."""
        self.loaded = False
        self._path_schemas.clear()

    def reload(self, *args: typing.Any, **kwargs: typing.Any) -> dict:
        """Reset internal caches and collect the specification again.

        Framework adapters expose ``load_specification`` with their native app
        argument. ``reload`` keeps that signature flexible so adapters can call
        it safely after routes or schemas change.
        """
        self.reset()
        load_specification = getattr(self, "load_specification", None)
        if callable(load_specification):
            return load_specification(*args, **kwargs)
        return self._load_specification()

    def _invalidate_schema_cache(self) -> None:
        self._path_schemas.clear()

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
            if self.version[0] == 2:
                schema_path = os.path.join(self.STATIC_DIR, "openapi2_schema.json")
            elif self.version[:2] == (3, 0):
                schema_path = os.path.join(self.STATIC_DIR, "openapi3.0_schema.yaml")
            elif self.version[:2] == (3, 1):
                schema_path = os.path.join(self.STATIC_DIR, "openapi3.1_schema.yaml")
            else:
                raise ValueError(
                    f"Unsupported OpenAPI specification version: {self.version}"
                )

        jsonschema_rs.JSONSchema(self.load_file(schema_path)).validate(
            self.specification
        )

    def add_schema(self, name: str, definition: dict[str, typing.Any]):
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
        self.reset()

    def add_path(
        self, path: str, specification: dict, method: typing.Optional[str] = None
    ):
        if "paths" not in self.specification:
            self.specification["paths"] = {}
        if path not in self.specification["paths"]:
            self.specification["paths"][path] = {}

        if method:
            self.specification["paths"][path][method.lower()] = specification
        else:
            self.specification["paths"][path] = specification
        self.reset()

    def _get_operation_parameters(
        self, path: str, method: str
    ) -> list[dict[str, typing.Any]]:
        path_item = self.specification["paths"][path]
        operation = path_item[method]
        parameters = []
        parameters.extend(path_item.get("parameters", []))
        parameters.extend(operation.get("parameters", []))
        return parameters

    def _parameter_schema(
        self, parameter: dict[str, typing.Any]
    ) -> typing.Optional[dict[str, typing.Any]]:
        if self.version[0] > 2:
            if "schema" not in parameter:
                return None
            return parameter["schema"]

        schema = {
            key: copy.deepcopy(parameter[key])
            for key in self.OPENAPI2_PARAMETER_SCHEMA_KEYS
            if key in parameter
        }
        if not schema:
            return None
        schema.pop("collectionFormat", None)
        return schema

    def _parameter_name(self, parameter: dict[str, typing.Any]) -> str:
        name = parameter["name"]
        if parameter.get("in") == "header":
            return name.lower()
        return name

    def _add_parameter_schema(
        self,
        target_schema: dict[str, typing.Any],
        parameter: dict[str, typing.Any],
    ) -> None:
        parameter_schema = self._parameter_schema(parameter)
        if parameter_schema is None:
            return
        name = self._parameter_name(parameter)
        target_schema["properties"][name] = parameter_schema
        if parameter.get("required", False) and name not in target_schema["required"]:
            target_schema["required"].append(name)

    def _normalize_media_type(self, content_type: str) -> str:
        message = Message()
        message["content-type"] = content_type or ""
        return message.get_content_type().lower()

    def _media_type_location(self, media_type: str) -> typing.Optional[str]:
        media_type = self._normalize_media_type(media_type)
        if media_type == "application/json" or media_type.endswith("+json"):
            return "json"
        if media_type in ("application/xml", "text/xml") or media_type.endswith("+xml"):
            return "xml"
        for location, media_types in self.VALIDATE_REQUEST_CONTENT_TYPES.items():
            if media_type in media_types:
                return location
        return None

    def _media_type_matches(self, location: str, expected: str, actual: str) -> bool:
        expected_type = self._normalize_media_type(expected)
        actual_type = self._normalize_media_type(actual)
        if actual_type == expected_type:
            return True
        return (
            location == "json"
            and expected_type == "application/json"
            and actual_type.endswith("+json")
        )

    def _request_body_schema(
        self, schema: dict[str, typing.Any], required: bool
    ) -> dict[str, typing.Any]:
        schema = copy.deepcopy(schema)
        if not required:
            return schema
        return {"allOf": [schema], "not": {"type": "null"}}

    def _openapi2_consumes(self, path: str, method: str) -> list[str]:
        operation = self.specification["paths"][path][method]
        consumes = operation.get("consumes") or self.specification.get("consumes")
        if consumes:
            return list(consumes)
        return list(self.VALIDATE_REQUEST_CONTENT_TYPES["json"])

    def _is_body_location(self, location: str) -> bool:
        return location in self.VALIDATE_REQUEST_CONTENT_TYPES

    def _get_path_schema(self, path: str, method: str):
        method = method.lower()
        cache_key = f"{path}_{method}"
        if cache_key in self._path_schemas:
            return self._path_schemas[cache_key]

        schema: dict[str, dict[str, typing.Any]] = {
            "query": {},
            "header": {},
            "path": {},
            "cookie": {},
            "json": {},
            "xml": {},
            "form": {},
            self.BODY_REQUIRED_KEY: {},
            self.BODY_MEDIA_TYPES_KEY: {},
        }
        if (
            "paths" not in self.specification
            or path not in self.specification["paths"]
            or method not in self.specification["paths"][path]
        ):
            return schema
        # parameters
        base_schema: dict[str, typing.Any] = {
            "type": "object",
            "properties": {},
            "required": [],
        }
        query_schema = copy.deepcopy(base_schema)
        header_schema = copy.deepcopy(base_schema)
        path_schema = copy.deepcopy(base_schema)
        cookie_schema = copy.deepcopy(base_schema)
        form_schema = copy.deepcopy(base_schema)
        for d in self._get_operation_parameters(path, method):
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
                body_schema = self._request_body_schema(
                    d["schema"], d.get("required", False)
                )
                for media_type in self._openapi2_consumes(path, method):
                    location = self._media_type_location(media_type)
                    if not location:
                        continue
                    schema[location] = body_schema
                    schema[self.BODY_MEDIA_TYPES_KEY].setdefault(location, []).append(
                        media_type
                    )
                continue
            else:
                continue
            self._add_parameter_schema(_schema, d)
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
            request_body = self.specification["paths"][path][method].get(
                "requestBody", {}
            )
            request_body = self.expand_specification(request_body)
            required = request_body.get("required", False)
            for media_type, media_schema in request_body.get("content", {}).items():
                location = self._media_type_location(media_type)
                if not location or "schema" not in media_schema:
                    continue
                schema[location] = self._request_body_schema(
                    media_schema["schema"], required
                )
                schema[self.BODY_MEDIA_TYPES_KEY].setdefault(location, []).append(
                    media_type
                )
        self._path_schemas[cache_key] = schema
        return schema

    def get_request_data(self, request: typing.Any, k: str) -> typing.Any:
        pass

    async def async_get_request_data(self, request: typing.Any, k: str) -> typing.Any:
        return self.get_request_data(request, k)

    def get_request_schema(self, request: typing.Any) -> dict:
        raise NotImplementedError

    def get_request_content_type(self, request: typing.Any) -> str:
        return request.headers.get("Content-Type", "") or request.headers.get(
            "content-type", ""
        )

    def _normalize_request_data(
        self, location: str, data: typing.Any, schema: dict[str, typing.Any]
    ) -> typing.Any:
        if location == "header" and isinstance(data, dict):
            data = {str(key).lower(): value for key, value in data.items()}

        if not isinstance(data, dict) or schema.get("type") != "object":
            return data

        properties = schema.get("properties", {})
        normalized = dict(data)
        for name, property_schema in properties.items():
            if name not in normalized:
                continue
            value = normalized[name]
            if property_schema.get("type") == "array":
                if not isinstance(value, list):
                    normalized[name] = [value]
            elif isinstance(value, list) and len(value) == 1:
                normalized[name] = value[0]
        return normalized

    def iter_request_schema(
        self, request: typing.Any, ignore: typing.Sequence[str] = tuple()
    ) -> typing.Generator[tuple[str, dict], None, None]:
        _ignore = set(ignore)
        schema = self.get_request_schema(request)
        body_media_types = schema.get(self.BODY_MEDIA_TYPES_KEY, {})
        body_schema_count = body_miss_count = 0
        for k, s in schema.items():
            if k.startswith("__") or not s or k in _ignore:
                continue
            if self._is_body_location(k):
                body_schema_count += 1
                expected_media_types = body_media_types.get(
                    k, self.VALIDATE_REQUEST_CONTENT_TYPES[k]
                )
                content_type = self.get_request_content_type(request)
                if not any(
                    self._media_type_matches(k, expected, content_type)
                    for expected in expected_media_types
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
            data = self._normalize_request_data(k, data, s)
            jsonschema_rs.JSONSchema(s).validate(data)

    async def async_validate_request(
        self, request: typing.Any, ignore: typing.Sequence[str] = tuple()
    ):
        for k, s in self.iter_request_schema(request, ignore=ignore):
            data = await self.async_get_request_data(request, k)
            data = self._normalize_request_data(k, data, s)
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

    def from_dict(self, content: dict) -> typing.Callable:
        def decorator(func: typing.Callable) -> typing.Callable:
            setattr(func, self.SPECIFICATION_DICT, content)
            return func

        return decorator

    def parse(self, func: typing.Callable) -> dict[str, typing.Any]:
        specification = {}
        if func.__doc__:
            try:
                specification = yaml.safe_load(func.__doc__.split("---")[-1])
            except yaml.error.YAMLError:
                specification = {}
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
    def load_file(file_path: str) -> dict:
        with open(file_path) as f:
            if file_path.endswith("json"):
                return json.load(f)
            else:
                return yaml.safe_load(f)

    @staticmethod
    def json_loads(content: typing.Union[str, bytes]) -> typing.Any:
        if not content:
            return None
        return json.loads(content)

    @staticmethod
    def xmltodict(content: typing.Union[str, bytes]):
        data = xmltodict.parse(content)

        for k in list(data.keys()):
            data = dict(data[k]) if isinstance(data[k], OrderedDict) else data[k]
            break
        return data
