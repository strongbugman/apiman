import typing
from collections import defaultdict
import json

from starlette.schemas import BaseSchemaGenerator
from starlette.routing import BaseRoute
import yaml


class SchemaGenerator(BaseSchemaGenerator):
    SWAGGER_PATH_ATTR_NAME = "__stagger_path__"

    def __init__(
        self,
        title: str = "Stagger",
        version: str = "0.1",
        description: str = "Api document",
        openapi_version: str = "2.0",
    ):
        self.schema: typing.Dict = {
            "info": {"title": title, "description": description, "version": version},
            "definitions": {},
            "paths": defaultdict(dict),
        }
        if openapi_version == "2.0":
            self.schema["swagger"] = openapi_version
        else:
            self.schema["openapi"] = openapi_version
        self.loaded = False

    @staticmethod
    def load_document(file_path: str) -> typing.Dict:
        with open(file_path) as f:
            if file_path.endswith("json"):
                return json.load(f)
            else:
                return yaml.safe_load(f)

    def add_definition(self, name, definition):
        self.schema["definitions"][name] = definition

    def add_path(self, path: str, method: str, document: typing.Dict):
        self.schema["paths"][path][method] = document

    def load_schema(self, routes: typing.List[BaseRoute]):
        for endpoint in self.get_endpoints(routes):
            doc_path: typing.Optional[str] = getattr(
                endpoint.func, self.SWAGGER_PATH_ATTR_NAME, None
            )

            if doc_path:
                doc = self.load_document(doc_path)
            else:
                doc = self.parse_docstring(endpoint.func)

            if doc:
                try:
                    definitions = doc.pop("definitions")
                except KeyError:
                    definitions = {}
                for name, definition in definitions.items():
                    self.add_definition(name, definition)

                self.add_path(endpoint.path, endpoint.http_method, doc)

        self.loaded = True

    def get_schema(self, routes: typing.List[BaseRoute]) -> typing.Dict:
        if not self.loaded:
            self.load_schema(routes)
        return self.schema

    def stagger_from(self, file_path: str) -> typing.Callable:
        def decorator(func: typing.Callable) -> typing.Callable:
            setattr(func, self.SWAGGER_PATH_ATTR_NAME, file_path)
            return func

        return decorator
