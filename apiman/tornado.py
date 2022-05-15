import json
import typing

from jinja2 import Template
from tornado.routing import Rule
from tornado.web import Application, RequestHandler

from .base import Apiman as _Apiman


class Apiman(_Apiman):
    """Tornado extension

    >>> apiman = Apiman(
    ...     template="./examples/docs/dog_template.yml"
    ... )
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
    >>> class MainHandler(tornado.web.RequestHandler):
    ...     @apiman.from_file("get.yml")
    ...     def get(self, path):
    ...         apiman.validate_request(self)
    ...         self.write(f"Hello, {path}")
    >>> app = tornado.web.Application(
    ...     [
    ...         (r"/hello/(.*)", MainHandler),
    ...     ]
    ... )
    >>> apiman.init_app(app)
    """

    def init_app(self, app: Application):
        if self.swagger_template and self.swagger_url:
            swagger_html = Template(open(self.swagger_template).read()).render(
                self.config
            )
            self.route(
                app,
                self.swagger_url,
                lambda self: self.write(swagger_html),
            )
        if self.redoc_template and self.redoc_template:
            redoc_html = Template(open(self.redoc_template).read()).render(self.config)
            self.route(app, self.redoc_url, lambda self: self.write(redoc_html))
        if self.specification_url:
            self.route(
                app,
                self.specification_url,
                lambda _self: _self.write(self.load_specification(app)),
            )

    def get_request_schema(self, handler: RequestHandler) -> typing.Dict:
        self.load_specification(handler.application)
        path = ""
        for rule in self._iter_rules(handler.application.default_router.rules):
            if rule.matcher.match(handler.request) and hasattr(rule.matcher, "regex"):
                path = rule.matcher.regex.pattern[:-1]  # type: ignore
                break
        return self._get_path_schema(
            self._covert_path_rule(path), handler.request.method.lower()  # type: ignore
        )

    def get_request_content_type(self, handler: RequestHandler) -> str:
        return handler.request.headers.get(
            "Content-Type", ""
        ) or handler.request.headers.get("content-type", "")

    def get_request_data(self, handler: RequestHandler, k: str) -> typing.Any:
        if k == "query":
            return {
                k: v[0].decode() for k, v in handler.request.query_arguments.items()
            }
        elif k == "path":
            data = {}
            for i, p in enumerate(handler.path_args):
                data[f"path{i}"] = p
            data.update(handler.path_kwargs)
            return data
        elif k == "cookie":
            data = {}
            for k, v in handler.cookies.items():
                data[k] = v.value
            return data
        elif k == "header":
            return dict(handler.request.headers)
        elif k == "json":
            return json.loads(handler.request.body)
        elif k == "form":
            return {k: v[0].decode() for k, v in handler.request.body_arguments.items()}
        elif k == "xml":
            return self.xmltodict(handler.request.body)
        else:
            return {}

    def load_specification(self, app: Application) -> typing.Dict:
        if not self.loaded:
            for rule in self._iter_rules(app.default_router.rules):
                if not hasattr(rule.matcher, "regex"):
                    continue
                handler = rule.target
                path = rule.matcher.regex.pattern[:-1]  # type: ignore
                # from class
                specification = self.parse(handler)
                if specification:
                    self.add_path(path, specification)
                # from class methods
                for method in self.HTTP_METHODS:
                    _func = getattr(handler, method.lower(), None)
                    if _func:
                        specification = self.parse(_func)
                        if specification:
                            self.add_path(path, specification, method=method)
            return self._load_specification()
        else:
            return self.specification

    def route(self, app: Application, url: str, func):
        app.add_handlers(
            ".*", [(url, type("Handler", (RequestHandler,), {"get": func}))]
        )

    def add_path(
        self, path: str, specification: typing.Dict, method: typing.Optional[str] = None
    ):
        return super().add_path(
            self._covert_path_rule(path), specification, method=method
        )

    def _covert_path_rule(self, path: str) -> str:
        # covert flask variable rules, eg "/path/(?P<id>.*)" to "/path/{id}"
        _subs = []
        i = 0
        for _sub in path.split("/"):
            if _sub.startswith("(") and _sub.endswith(")"):
                if "?P<" in _sub:
                    _subs.append(f"{{{_sub.split('<')[-1].split('>')[0]}}}")
                else:
                    _subs.append(f"{{path{i}}}")
                    i += 1
            else:
                _subs.append(_sub)

        return "/".join(_subs)

    def _iter_rules(
        self, rules: typing.List[Rule]
    ) -> typing.Generator[Rule, None, None]:
        for rule in rules:
            if hasattr(rule.target, "rules"):
                for r in self._iter_rules(rule.target.rules):
                    yield r
            else:
                yield rule


Extension = Apiman
