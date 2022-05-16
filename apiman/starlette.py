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
        app.on_event("startup")(lambda: self.load_specification(app))

        if self.swagger_template and self.swagger_url:
            swagger_html = Template(open(self.swagger_template).read()).render(
                self.config
            )
            self.route(app, self.swagger_url, lambda _: Response(swagger_html))
        if self.redoc_template and self.redoc_template:
            redoc_html = Template(open(self.redoc_template).read()).render(self.config)
            self.route(app, self.redoc_url, lambda _: Response(redoc_html))
        if self.specification_url:
            self.route(
                app,
                self.specification_url,
                lambda _: JSONResponse(self.load_specification(app)),
            )
        self.router = app.router

    def get_request_schema(self, request: Request) -> typing.Dict:
        # get regex path, eg: "/api/cats/{id}/"
        path = ""
        for r in self.router.routes:
            scope = r.matches(request.scope)[1]
            if scope:
                path = getattr(r, "path", "") or scope.get("path", "")
                break
        return self._get_path_schema(path, request.method.lower())

    def get_request_data(self, request: Request, k: str) -> typing.Any:
        if k == "query":
            return request.query_params._dict
        elif k == "path":
            return request.path_params
        elif k == "cookie":
            return request.cookies
        elif k == "header":
            return dict(request.headers)
        elif k == "json":
            return getattr(request, "_json", {})
        elif k == "form":
            return dict(getattr(request, "_form", {}))
        elif k == "xml":
            return self.xmltodict(getattr(request, "_body", ""))
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

    def load_specification(
        self, app: Starlette, mount: typing.Optional[Mount] = None, base_path=""
    ) -> typing.Dict:
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
