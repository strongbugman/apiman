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
        if self.redoc_template and self.redoc_url:
            redoc_html = Template(open(self.redoc_template).read()).render(self.config)
            (
                self.route(
                    app,
                    self.redoc_url,
                    lambda req, res: (
                        setattr(res, "text", redoc_html),  # type: ignore
                        setattr(res, "content_type", "html"),  # type: ignore
                    ),
                ),
            )
        if self.specification_url:
            self.route(
                app,
                self.specification_url,
                lambda req, res: (
                    setattr(res, "text", json.dumps(self.load_specification(app))),  # type: ignore
                    setattr(res, "content_type", "application/json"),  # type: ignore
                ),
            )

    def get_request_schema(self, request: Request) -> dict:
        self.load_specification(None)
        return self._get_path_schema(
            self._covert_path_rule(request.uri_template), request.method.lower()
        )

    def get_request_data(self, request: Request, k: str) -> typing.Any:
        if k == "query":
            return request.params
        elif k == "path":
            return self._get_request_path_params(request)
        elif k == "cookie":
            return request.cookies
        elif k == "header":
            return {key.lower(): value for key, value in request.headers.items()}
        elif k in ("json", "form", "xml"):
            return self._get_request_media(request)
        else:
            return {}

    async def async_get_request_data(self, request: Request, k: str) -> typing.Any:
        if k in ("json", "form", "xml"):
            await request.get_media()
        return self.get_request_data(request, k)

    def _get_request_path_params(self, request: Request) -> dict[str, str]:
        try:
            _, params, *_ = self.app._get_responder(request)
        except (AttributeError, TypeError, ValueError):
            return {}
        return dict(params)

    def _get_request_media(self, request: Request) -> typing.Any:
        if isinstance(request, ASGIRequest):
            return getattr(request, "_media", None)
        return request.media

    def _iter_router_roots(self) -> list[CompiledRouterNode]:
        try:
            return list(self.app._router._roots)
        except AttributeError:
            return []

    def _load_node_specification(self, nodes: list[CompiledRouterNode]):
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

    def load_specification(self, _) -> dict:
        if not self.loaded:
            self._load_node_specification(self._iter_router_roots())
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
        self, path: str, specification: dict, method: typing.Optional[str] = None
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
