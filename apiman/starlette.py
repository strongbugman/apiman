import typing

from starlette.applications import Starlette
from starlette.responses import Response, JSONResponse
from starlette.schemas import SchemaGenerator
from jinja2 import Template

from .openapi import OpenApi


class Extension(OpenApi):
    def init_app(self, app: Starlette):
        if self.config["swagger_template"] and self.config["swagger_url"]:
            swagger_html = Template(
                open(self.config["swagger_template"]).read()
            ).render(self.config)
            app.add_route(
                self.config["swagger_url"],
                lambda _: Response(swagger_html),
                methods=["GET"],
                include_in_schema=False,
            )
        if self.config["redoc_template"] and self.config["redoc_url"]:
            redoc_html = Template(open(self.config["redoc_template"]).read()).render(
                self.config
            )
            app.add_route(
                self.config["redoc_url"],
                lambda _: Response(redoc_html),
                methods=["GET"],
                include_in_schema=False,
            )
        if self.config["specification_url"]:
            app.add_route(
                self.config["specification_url"],
                lambda _: JSONResponse(self.load_specification(app)),
                methods=["GET"],
                include_in_schema=False,
            )

    def load_specification(self, app: Starlette) -> typing.Dict:
        if app.debug or not self.loaded:
            for endpoint in SchemaGenerator({}).get_endpoints(app.routes):
                specification = self.from_func(endpoint.func)
                if specification:
                    self._load_specification(
                        endpoint.path, endpoint.http_method, specification
                    )
            self.loaded = True
            return self.specification
        else:
            return self.specification
