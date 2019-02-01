import typing
from functools import partial

from starlette.applications import Starlette

from .endpoints import SwaggerUI, RedocUI, Schema
from .generators import SchemaGenerator


class Starchart:
    """A extension to handle starchart's config"""

    def __init__(
        self,
        title="Starchart",
        description="Api document",
        version="0.1",
        openapi_version="3.0.0",
        schema_path="/docs/schema/",
        doc_path="/docs/",
    ):
        self.schema_generator = SchemaGenerator(
            title=title,
            description=description,
            version=version,
            openapi_version=openapi_version,
        )
        SwaggerUI.set_schema_url(schema_path)
        RedocUI.set_schema_url(schema_path)
        self.doc_path = doc_path
        self.schema_path = schema_path
        self.app: typing.Optional[Starlette] = None

    def register(self, app: Starlette):
        self.app = app
        app.add_event_handler("startup", self.startup)

    def startup(self):
        self.schema_generator.load_schema(self.app.routes)
        Schema.set_schema_loader(
            partial(self.schema_generator.get_schema, self.app.routes)
        )

        self.app.add_route(
            self.schema_path,
            Schema,
            methods=["GET"],
            name="SwaggerSchema",
            include_in_schema=False,
        )
        self.app.add_route(
            f"{self.doc_path}swagger/",
            SwaggerUI,
            methods=["GET"],
            name="SwaggerUI",
            include_in_schema=False,
        )
        self.app.add_route(
            f"{self.doc_path}redoc/",
            RedocUI,
            methods=["GET"],
            name="SwaggerUI",
            include_in_schema=False,
        )
        self.app.schema_generator = self.schema_generator
