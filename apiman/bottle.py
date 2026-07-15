import typing

from bottle import Bottle, Request
from jinja2 import Template

from .base import Apiman as _Apiman


class Apiman(_Apiman):
    """Bottle extension

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

    def init_app(self, app: Bottle):
        app.add_hook("before_request", lambda: self.load_specification(app))

        if self.swagger_template and self.swagger_url:
            swagger_html = Template(open(self.swagger_template).read()).render(
                self.config
            )
            self.route(
                app,
                self.swagger_url,
                lambda: swagger_html,
            )
        if self.redoc_template and self.redoc_url:
            redoc_html = Template(open(self.redoc_template).read()).render(self.config)
            self.route(app, self.redoc_url, lambda: redoc_html)
        if self.specification_url:
            self.route(
                app,
                self.specification_url,
                lambda: self.load_specification(app),
            )

    def get_request_schema(self, request: Request) -> dict:
        return self._get_path_schema(
            self._covert_path_rule(request.route.rule), request.method.lower()
        )

    def get_request_data(self, request: Request, k: str) -> typing.Any:
        if k == "query":
            data = {}
            for key in request.query:
                values = request.query.getall(key)
                data[key] = values if len(values) > 1 else values[0]
            return data
        elif k == "path":
            return dict(request.url_args)
        elif k == "cookie":
            return dict(request.cookies)
        elif k == "header":
            return {key.lower(): value for key, value in dict(request.headers).items()}
        elif k == "json":
            return request.json
        elif k == "form":
            return dict(request.forms)
        elif k == "xml":
            return self.xmltodict(request.body)
        else:
            return {}

    def load_specification(self, app: Bottle) -> dict:
        if not self.loaded:
            for route in app.routes:
                func = route.callback
                specification = self.parse(func)
                if not specification:
                    continue
                if (
                    set(specification.keys()) & self.HTTP_METHODS
                ):  # multi method description
                    self.add_path(route.rule, specification)
                elif route.method.lower() in self.HTTP_METHODS:
                    self.add_path(route.rule, specification, method=route.method)
            return self._load_specification()
        else:
            return self.specification

    def route(self, app: Bottle, url: str, func):
        app.route(url)(func)

    def add_path(
        self, path: str, specification: dict, method: typing.Optional[str] = None
    ):
        return super().add_path(
            self._covert_path_rule(path), specification, method=method
        )

    def _covert_path_rule(self, path: str) -> str:
        # covert flask variable rules, eg "/path/<id:int>" to "/path/{id}"
        _subs = []
        for _sub in path.split("/"):
            if _sub.startswith("<") and _sub.endswith(">"):
                _subs.append(f"{{{_sub[1:-1].split(':')[0]}}}")
            else:
                _subs.append(_sub)

        return "/".join(_subs)


Extension = Apiman
