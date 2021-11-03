import os
import typing

from jinja2 import Template
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from .openapi import OpenApi

EndpointFunc = typing.Callable[
    [Request], typing.Union[Response, typing.Coroutine[None, None, Response]]
]


class Extension(OpenApi):
    def __init__(
        self,
        decorators: typing.Sequence[
            typing.Callable[[EndpointFunc], EndpointFunc]
        ] = tuple(),
        title="OpenAPI Document",
        specification_url="/apiman/specification/",
        swagger_url="/apiman/swagger/",
        redoc_url="/apiman/redoc/",
        swagger_template=os.path.join(OpenApi.STATIC_DIR, "swagger.html"),
        redoc_template=os.path.join(OpenApi.STATIC_DIR, "redoc.html"),
        template=os.path.join(OpenApi.STATIC_DIR, "template.yml"),
    ):
        """Starlette extention

        >>> app = Starlette()
        >>> openapi = Extension(
        ...     template="./examples/docs/cat_template.yml", decorators=(lambda f: f,)
        ... )
        >>> openapi.init_app(app)
        >>> openapi.add_schema(
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
        ... @openapi.from_file("./examples/docs/cats_get.yml")
        ... def list_cats(req: Request):
        ...     return JSONResponse(list(CATS.values()))
        """
        super().__init__(
            title=title,
            specification_url=specification_url,
            swagger_url=swagger_url,
            redoc_url=redoc_url,
            swagger_template=swagger_template,
            redoc_template=redoc_template,
            template=template,
        )
        self.decorators = decorators

    def init_app(self, app: Starlette):
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
                        specification = self.from_func(route.endpoint)
                        if specification:
                            self._load_specification(
                                base_path + route.path, specification
                            )
                        # load from single method
                        for method in self.HTTP_METHODS:
                            func = getattr(route.endpoint, method, None)
                            if func:
                                specification = self.from_func(func)
                                if specification:
                                    self._load_specification(
                                        base_path + route.path,
                                        specification,
                                        method=method,
                                    )
                    else:  # for endpoint function
                        specification = self.from_func(route.endpoint)
                        if specification:
                            if (
                                set(specification.keys()) & self.HTTP_METHODS
                            ):  # multi method description
                                self._load_specification(
                                    base_path + route.path, specification
                                )
                            elif route.methods:
                                for method in route.methods:
                                    if method.lower() in self.HTTP_METHODS:
                                        self._load_specification(
                                            base_path + route.path,
                                            specification,
                                            method=method,
                                        )

            self.loaded = True
            return self.specification
        else:
            return self.specification

    def route(self, app: Starlette, url: str, func: EndpointFunc):
        for decorator in self.decorators:
            func = decorator(func)
        app.add_route(url, func, methods=["GET"], include_in_schema=False)
