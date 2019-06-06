import typing

from flask import Flask, jsonify, Response
from jinja2 import Template

from .openapi import OpenApi


class Extension(OpenApi):
    def __init__(
        self,
        *args,
        app: typing.Optional[Flask] = None,
        decorators: typing.Sequence[
            typing.Callable[[typing.Callable], typing.Callable]
        ] = tuple(),
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.app = app
        self.decorators = decorators
        self.init_app(self.app) if self.app else None

    def init_app(self, app: Flask):
        app.extensions["apiman"] = self

        self.config.update(app.config.get_namespace("OPENAPI_", lowercase=True))

        if self.config["swagger_template"] and self.config["swagger_url"]:
            swagger_html = Template(
                open(self.config["swagger_template"]).read()
            ).render(self.config)
            self.route(
                app,
                self.config["swagger_url"],
                "swagger_ui",
                lambda: Response(swagger_html),
            )
        if self.config["redoc_template"] and self.config["redoc_url"]:
            redoc_html = Template(open(self.config["redoc_template"]).read()).render(
                self.config
            )
            self.route(
                app, self.config["redoc_url"], "redoc_ui", lambda: Response(redoc_html)
            )
        if self.config["specification_url"]:
            self.route(
                app,
                self.config["specification_url"],
                "openapi_specification",
                lambda: jsonify(self.load_specification(app)),
            )

    def load_specification(self, app: Flask) -> typing.Dict:
        if app.debug or not self.loaded:
            for route in app.url_map.iter_rules():
                func = app.view_functions[route.endpoint]
                if hasattr(func, "view_class"):  # view class
                    # from class
                    specification = self.from_func(
                        func.view_class
                    )  # the specification include multi method description
                    if set(specification.keys()) & self.HTTP_METHODS:
                        for method in specification.keys():
                            self._load_specification(
                                route.rule, method, specification[method]
                            )
                    # from class methods
                    for method in route.methods:
                        try:
                            _func = getattr(func.view_class, method.lower())
                        except AttributeError:
                            continue
                        specification = self.from_func(_func)
                        if specification:
                            self._load_specification(route.rule, method, specification)
                else:  # view function
                    specification = self.from_func(func)
                    if not specification:
                        continue
                    if set(specification.keys()) & self.HTTP_METHODS:
                        for method in specification.keys():
                            self._load_specification(
                                route.rule, method, specification[method]
                            )
                    else:
                        for method in route.methods:
                            # Almost HEAD or OPTIONS set by flask, ignore by default
                            if method in ("HEAD", "OPTIONS"):
                                continue
                            self._load_specification(route.rule, method, specification)
            self.loaded = True
            return self.specification
        else:
            return self.specification

    def route(self, app: Flask, url: str, endpoint: str, func):
        for decorator in self.decorators:
            func = decorator(func)
        app.route(url, endpoint=endpoint, methods=["GET"])(func)
