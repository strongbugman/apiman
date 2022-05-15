import typing

from flask import Flask, Request, Response, jsonify
from jinja2 import Template

from .base import Apiman as _Apiman


class Apiman(_Apiman):
    """Flask extension

    >>> app = Flask(__name__)
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
    >>> @app.route("/dogs/", methods=["GET"])
    ... @apiman.from_file("./examples/docs/dogs_get.yml")
    ... def list_dogs():
    ...     return jsonify(list(DOGS.values()))
    """

    def init_app(self, app: Flask):
        app.extensions["apiman"] = self
        app.before_first_request(lambda: self.load_specification(app))  # type: ignore

        if self.swagger_template and self.swagger_url:
            swagger_html = Template(open(self.swagger_template).read()).render(
                self.config
            )
            self.route(
                app,
                self.swagger_url,
                "swagger_ui",
                lambda: Response(swagger_html),
            )
        if self.redoc_template and self.redoc_template:
            redoc_html = Template(open(self.redoc_template).read()).render(self.config)
            self.route(app, self.redoc_url, "redoc_ui", lambda: Response(redoc_html))
        if self.specification_url:
            self.route(
                app,
                self.specification_url,
                "apiman_specification",
                lambda: jsonify(self.load_specification(app)),
            )

    def get_request_schema(self, request: Request) -> typing.Dict:
        if request.url_rule:
            path = self._covert_path_rule(request.url_rule.rule)
        else:
            path = request.path
        return self._get_path_schema(path, request.method.lower())

    def get_request_data(self, request: Request, k: str) -> typing.Any:
        if k == "query":
            return dict(request.args)
        elif k == "path":
            return request.view_args or {}
        elif k == "cookie":
            return dict(request.cookies)
        elif k == "header":
            return dict(request.headers.items())
        elif k == "json":
            return request.json
        elif k == "form":
            return dict(request.form)
        elif k == "xml":
            return self.xmltodict(request.data)
        else:
            return {}

    def load_specification(self, app: Flask) -> typing.Dict:
        if not self.loaded:
            for route in app.url_map.iter_rules():
                func = app.view_functions[route.endpoint]
                if hasattr(func, "view_class"):  # view class
                    # from class
                    specification = self.parse(func.view_class)  # type: ignore
                    if specification:
                        self.add_path(route.rule, specification)
                    # from class methods
                    for method in route.methods:  # type: ignore
                        _func = getattr(func.view_class, method.lower(), None)  # type: ignore
                        if _func:
                            specification = self.parse(_func)
                            if specification:
                                self.add_path(route.rule, specification, method=method)
                else:  # view function
                    specification = self.parse(func)
                    if not specification:
                        continue
                    if (
                        set(specification.keys()) & self.HTTP_METHODS
                    ):  # multi method description
                        self.add_path(route.rule, specification)
                    else:
                        for method in route.methods:  # type: ignore
                            if method.lower() in self.HTTP_METHODS:
                                self.add_path(route.rule, specification, method=method)
            return self._load_specification()
        else:
            return self.specification

    def route(self, app: Flask, url: str, endpoint: str, func):
        app.route(url, endpoint=endpoint, methods=["GET"])(func)

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
            if _sub.startswith("<") and _sub.endswith(">"):
                _subs.append(f"{{{_sub[1:-1].split(':')[-1]}}}")
            else:
                _subs.append(_sub)

        return "/".join(_subs)


Extension = Apiman
