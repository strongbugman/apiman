import typing

from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from jinja2 import Template

import starchart


class UI(HTTPEndpoint):
    TEMPLATE = Template(open(f"{starchart.__path__[0]}/static/index.html").read())
    CONTEXT = {"title": "Starchart", "schema_url": "./schema/", "request": None}

    def get(self, res: Request) -> Response:
        self.CONTEXT["request"] = res
        return Response(self.TEMPLATE.render(self.CONTEXT))

    @classmethod
    def set_template(cls, path: str) -> None:
        cls.TEMPLATE = Template(open(path).read())

    @classmethod
    def set_schema_url(cls, schema_url: str) -> None:
        cls.CONTEXT["schema_url"] = schema_url

    @classmethod
    def set_title(cls, tilte: str) -> None:
        cls.CONTEXT["title"] = tilte


class SwaggerUI(UI):
    TEMPLATE = Template(
        open(f"{starchart.__path__[0]}/static/swagger_index.html").read()
    )


class RedocUI(UI):
    TEMPLATE = Template(open(f"{starchart.__path__[0]}/static/redoc_index.html").read())


class Schema(HTTPEndpoint):
    SCHEMA_LOADER: typing.Callable[[], typing.Dict] = lambda: dict

    def get(self, res: Request) -> JSONResponse:
        return JSONResponse(self.SCHEMA_LOADER())

    @classmethod
    def set_schema_loader(cls, loader: typing.Callable[[], typing.Dict]) -> None:
        cls.SCHEMA_LOADER = loader
