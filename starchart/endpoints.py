import typing

from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import TemplateResponse, JSONResponse
from jinja2 import Template

import starchart


class UI(HTTPEndpoint):
    TEMPLATE = Template(open(f"{starchart.__path__[0]}/static/index.html").read())
    CONTEXT = {
        "title": "Swagger UI",
        "swagger_ui_css": "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.20.5"
        "/swagger-ui.css",
        "swagger_ui_bundle_js": "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3"
        ".20.5/swagger-ui-bundle.js",
        "swagger_ui_standalone_preset_js": "https://cdnjs.cloudflare.com/ajax/libs/swagger-ui/3.20.5/swagger-ui-standalone-preset.js",
        "schema_url": "./schema/",
        "request": None,
    }

    def get(self, res: Request):
        self.CONTEXT["request"] = res
        return TemplateResponse(self.TEMPLATE, self.CONTEXT)


class Schema(HTTPEndpoint):
    SCHEMA_LOADER: typing.Callable[[], typing.Dict] = lambda: dict

    def get(self, res: Request):
        return JSONResponse(self.SCHEMA_LOADER())
