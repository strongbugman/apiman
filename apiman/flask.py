import typing

from flask import Flask, jsonify, Response
from jinja2 import Template

from .openapi import OpenApi


class Extension(OpenApi):
    def init_app(self, app: Flask):
        self.config.update(app.config.get_namespace("OPNEAPI_", lowercase=True))

        if self.config["swagger_template"] and self.config["swagger_url"]:
            swagger_html = Template(
                open(self.config["swagger_template"]).read()
            ).render(self.config)
            app.route(
                self.config["swagger_url"], methods=["GET"], endpoint="swagger_ui"
            )(lambda: Response(swagger_html))
        if self.config["redoc_template"] and self.config["redoc_url"]:
            redoc_html = Template(open(self.config["redoc_template"]).read()).render(
                self.config
            )
            app.route(self.config["redoc_url"], methods=["GET"], endpoint="redoc_ui")(
                lambda: Response(redoc_html)
            )
        if self.config["specification_url"]:
            app.route(
                self.config["specification_url"], endpoint="openapi_specification"
            )(lambda: jsonify(self.load_specification(app)))

    def load_specification(self, app: Flask) -> typing.Dict:
        if app.debug or not self.loaded:
            for route in app.url_map.iter_rules():
                func = app.view_functions[route.endpoint]
                if hasattr(func, "view_class"):  # view class
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
                    if set(specification.keys()) & {
                        "head",
                        "get",
                        "post",
                        "put",
                        "patch",
                        "delete",
                        "options",
                    }:
                        # the specification include multi method descriptino
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
