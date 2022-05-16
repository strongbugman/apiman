import json
import re
import typing

from falcon import App, Request
from falcon.asgi import App as ASGIApp
from falcon.asgi import Request as ASGIRequest
from falcon.routing.compiled import CompiledRouterNode
from jinja2 import Template

from .base import Apiman as _Apiman


class Apiman(_Apiman):
    """Falcon extension

    >>> app = App()
    >>> apiman = Apiman(
    ...     template="./examples/docs/dog_template.yml"
    ... )
    >>> apiman.init_app(app)
    >>> apiman.add_schema(
    ...     "Dog",
    ...     {
    ...         "properties": {
    ...             "id": {"description": "global unique", "type": "integer"},
    ...             "name": {"type": "string"},
    ...             "age": {"type": "integer"},
    ...         },
    ...         "type": "object",
    ...     },
    ... )
    >>> app.add_route("/echo/{name}", ThingsResource())
    """

    PATH_VAR_REGEX = re.compile(r"\{(.*?)\}")

    @property
    def app(self) -> App:
        assert hasattr(self, "_app"), "call init_app first"
        return self._app

    def init_app(self, app: App):
        self._app = app
        if self.swagger_template and self.swagger_url:
            swagger_html = Template(open(self.swagger_template).read()).render(
                self.config
            )
            self.route(
                app,
                self.swagger_url,
                lambda req, res: (
                    setattr(res, "text", swagger_html),  # type: ignore
                    setattr(res, "content_type", "html"),  # type: ignore
                ),
            )
        if self.redoc_template and self.redoc_template:
            redoc_html = Template(open(self.redoc_template).read()).render(self.config)
            self.route(
                app,
                self.redoc_url,
                lambda req, res: (
                    setattr(res, "text", redoc_html),  # type: ignore
                    setattr(res, "content_type", "html"),  # type: ignore
                ),
            ),
        if self.specification_url:
            self.route(
                app,
                self.specification_url,
                lambda req, res: (
                    setattr(res, "text", json.dumps(self.load_specification(app))),  # type: ignore
                    setattr(res, "content_type", "application/json"),  # type: ignore
                ),
            )

    def get_request_schema(self, request: Request) -> typing.Dict:
        self.load_specification(None)
        return self._get_path_schema(
            self._covert_path_rule(request.uri_template), request.method.lower()
        )

    def get_request_data(self, request: Request, k: str) -> typing.Any:
        if k == "query":
            return request.params
        elif k == "path":
            return self.app._get_responder(request)[1]
        elif k == "cookie":
            return request.cookies
        elif k == "header":
            return request.headers
        elif k in ("json", "form", "xml"):
            if isinstance(request, ASGIRequest):
                return request._media
            else:
                return request.media
        else:
            return {}

    async def async_get_request_data(self, request: Request, k: str) -> typing.Any:
        if k in ("json", "form", "xml"):
            await request.get_media()
        return self.get_request_data(request, k)

    def _load_node_specification(self, nodes: typing.List[CompiledRouterNode]):
        for n in nodes:
            if n.resource:
                # from class
                specification = self.parse(n.resource.__class__)  # type: ignore
                if specification:
                    self.add_path(n.uri_template, specification)
                # from class methods
                for method in self.HTTP_METHODS:  # type: ignore
                    _func = getattr(n.resource.__class__, f"on_{method.lower()}", None)  # type: ignore
                    if _func:
                        specification = self.parse(_func)
                        if specification:
                            self.add_path(n.uri_template, specification, method=method)
            self._load_node_specification(n.children)

    def load_specification(self, _) -> typing.Dict:
        if not self.loaded:
            self._load_node_specification(self.app._router._roots)
            return self._load_specification()
        else:
            return self.specification

    def route(self, app: App, url: str, func):
        class ASGIResource:
            async def on_get(self, req, res):
                func(req, res)

        class Resource:
            def on_get(self, req, res):
                func(req, res)

        app.add_route(url, ASGIResource() if isinstance(app, ASGIApp) else Resource())

    def add_path(
        self, path: str, specification: typing.Dict, method: typing.Optional[str] = None
    ):
        return super().add_path(
            self._covert_path_rule(path), specification, method=method
        )

    def _covert_path_rule(self, path: str) -> str:
        # covert flask variable rules, eg "/path/<int:id>" to "/path/{id}"
        _subs = []
        for _sub in path.split("/"):
            for _p in self.PATH_VAR_REGEX.findall(_sub):
                _sub = _sub.replace(_p, _p.split(":")[0])
            _subs.append(_sub)

        return "/".join(_subs)


Extension = Apiman
