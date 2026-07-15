import typing

from jinja2 import Template
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from .base import Apiman as _Apiman


class Apiman(_Apiman):
    """Starlette extention

    >>> app = Starlette()
    >>> apiman = Apiman(
    ...     template="./examples/docs/cat_template.yml",
    ... )
    >>> apiman.init_app(app)
    >>> apiman.add_schema(
    ...     "Cat",
    ...     {
    ...         "properties": {
    ...             "id": {"description": "global unique", "type": "integer"},
    ...             "name": {"type": "string"},
    ...             "age": {"type": "integer"},
    ...         },
    ...         "type": "object",
    ...     },
    ... )
    >>> @app.route("/cats/", methods=["GET"])
    ... @apiman.from_file("./examples/docs/cats_get.yml")
    ... def list_cats(req: Request):
    ...     return JSONResponse(list(CATS.values()))
    """

    def init_app(self, app: Starlette):
        self._app = app
        app.on_event("startup")(lambda: self.load_specification(app))

        if self.swagger_template and self.swagger_url:
            swagger_html = Template(open(self.swagger_template).read()).render(
                self.config
            )
            self.route(app, self.swagger_url, lambda _: Response(swagger_html))
        if self.redoc_template and self.redoc_url:
            redoc_html = Template(open(self.redoc_template).read()).render(self.config)
            self.route(app, self.redoc_url, lambda _: Response(redoc_html))
        if self.specification_url:
            self.route(
                app,
                self.specification_url,
                lambda _: JSONResponse(self.load_specification(app)),
            )
        self.router = app.router

    def get_request_schema(self, request: Request) -> dict:
        # get regex path, eg: "/api/cats/{id}/"
        route = request.scope.get("route")
        path = getattr(route, "path", "") if route else ""
        for r in self.router.routes:
            if path:
                break
            match, scope = r.matches(request.scope)
            if match.value:
                path = getattr(r, "path", "") or scope.get("path", "")
                break
        return self._get_path_schema(path, request.method.lower())

    _UNREAD = object()

    def _cached_request_value(self, request: Request, name: str) -> typing.Any:
        # Starlette only populates these private cache attributes after the
        # matching async accessor (request.json()/.form()/.body()) has been
        # awaited at least once. Reading them before that silently returns a
        # falsy default and drops the request body from validation, so fail
        # loudly instead when the body was never actually read.
        value = getattr(request, name, self._UNREAD)
        if value is self._UNREAD or (name == "_form" and value is None):
            raise RuntimeError(
                f"Starlette request body ({name!r}) was not read before "
                "validation. Use `await apiman.async_validate_request(request)` "
                "instead of the sync `validate_request` for routes with a "
                "JSON/form/XML body."
            )
        return value

    def get_request_data(self, request: Request, k: str) -> typing.Any:
        if k == "query":
            data: dict[str, typing.Any] = {}
            # e.g. [("tag", "red"), ("tag", "blue")]
            #   -> {"tag": ["red", "blue"]}
            for key, value in request.query_params.multi_items():
                if key in data:
                    current = data[key]
                    if isinstance(current, list):
                        current.append(value)
                    else:
                        data[key] = [current, value]
                else:
                    data[key] = value
            return data
        elif k == "path":
            return request.path_params
        elif k == "cookie":
            return request.cookies
        elif k == "header":
            return {key.lower(): value for key, value in request.headers.items()}
        elif k == "json":
            return self._cached_request_value(request, "_json")
        elif k == "form":
            form = self._cached_request_value(request, "_form")
            form_data: dict[str, typing.Any] = {}
            # FormData is a MultiDict; dict(form) would silently keep only the
            # last value. e.g. [("tag", "red"), ("tag", "blue")]
            #   -> {"tag": ["red", "blue"]}
            for key, value in form.multi_items():
                if key not in form_data:
                    form_data[key] = value
                elif isinstance(form_data[key], list):
                    form_data[key].append(value)
                else:
                    form_data[key] = [form_data[key], value]
            return form_data
        elif k == "xml":
            return self.xmltodict(self._cached_request_value(request, "_body"))
        else:
            return {}

    async def async_get_request_data(self, request: Request, k: str) -> typing.Any:
        if k == "json":
            await request.json()
        elif k == "form":
            await request.form()
        elif k == "xml":
            await request.body()

        return self.get_request_data(request, k)

    def has_request_body(self, request: Request, location: str) -> bool:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                return int(content_length) > 0
            except ValueError:
                pass
        body = getattr(request, "_body", None)
        if body is not None:
            return bool(body)
        if location == "form":
            form = getattr(request, "_form", None)
            return bool(form)
        return False

    def load_specification(
        self,
        app: typing.Optional[Starlette] = None,
        mount: typing.Optional[Mount] = None,
        base_path="",
    ) -> dict:
        app = app or self._app
        if not self.loaded:
            for route in mount.routes if mount else app.routes:
                if isinstance(route, Mount) and route.routes:
                    self.loaded = False
                    self.load_specification(
                        app, mount=route, base_path=base_path + route.path
                    )
                elif isinstance(route, Route):
                    if not route.include_in_schema:
                        continue

                    if isinstance(route.endpoint, type):  # for endpoint class
                        # load from endpoint class
                        specification = self.parse(route.endpoint)
                        if specification:
                            self.add_path(base_path + route.path, specification)
                        # load from single method
                        for method in self.HTTP_METHODS:
                            func = getattr(route.endpoint, method, None)
                            if func:
                                specification = self.parse(func)
                                if specification:
                                    self.add_path(
                                        base_path + route.path,
                                        specification,
                                        method=method,
                                    )
                    else:  # for endpoint function
                        specification = self.parse(route.endpoint)
                        if specification:
                            if (
                                set(specification.keys()) & self.HTTP_METHODS
                            ):  # multi method description
                                self.add_path(base_path + route.path, specification)
                            elif route.methods:
                                for method in route.methods:
                                    if method.lower() in self.HTTP_METHODS:
                                        self.add_path(
                                            base_path + route.path,
                                            specification,
                                            method=method,
                                        )

            return self._load_specification()
        else:
            return self.specification

    def route(self, app: Starlette, url: str, func: typing.Callable):
        app.add_route(url, func, methods=["GET"], include_in_schema=False)


Extension = Apiman
