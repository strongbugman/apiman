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
        self._app = app
        if self.swagger_template and self.swagger_url:
            swagger_html = Template(open(self.swagger_template).read()).render(
                self.config
            )
            self.route(
                app,
                self.swagger_url,
                lambda self: self.write(swagger_html),
            )
        if self.redoc_template and self.redoc_url:
            redoc_html = Template(open(self.redoc_template).read()).render(self.config)
            self.route(app, self.redoc_url, lambda self: self.write(redoc_html))
        if self.specification_url:
            self.route(
                app,
                self.specification_url,
                lambda _self: _self.write(self.load_specification(app)),
            )

    def get_request_schema(self, handler: RequestHandler) -> dict:
        self.load_specification(handler.application)
        path = ""
        for rule in self._iter_rules(self._application_rules(handler.application)):
            rule_path = self._rule_path(rule)
            if rule_path and rule.matcher.match(handler.request):
                path = rule_path
                break
        return self._get_path_schema(
            self._covert_path_rule(path),
            handler.request.method.lower(),  # type: ignore
        )

    def get_request_content_type(self, handler: RequestHandler) -> str:
        return handler.request.headers.get(
            "Content-Type", ""
        ) or handler.request.headers.get("content-type", "")

    def get_request_data(self, handler: RequestHandler, k: str) -> typing.Any:
        if k == "query":
            return {
                k: [item.decode() for item in v] if len(v) > 1 else v[0].decode()
                for k, v in handler.request.query_arguments.items()
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
            return {
                key.lower(): value
                for key, value in dict(handler.request.headers).items()
            }
        elif k == "json":
            return self.json_loads(handler.request.body)
        elif k == "form":
            return {
                k: [item.decode() for item in v] if len(v) > 1 else v[0].decode()
                for k, v in handler.request.body_arguments.items()
            }
        elif k == "xml":
            return self.xmltodict(handler.request.body)
        else:
            return {}

    def has_request_body(self, request: RequestHandler, location: str) -> bool:
        _ = location
        return bool(request.request.body)

    def load_specification(self, app: typing.Optional[Application] = None) -> dict:
        app = app or self._app
        if not self.loaded:
            for rule in self._iter_rules(self._application_rules(app)):
                path = self._rule_path(rule)
                if not path:
                    continue
                handler = rule.target
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
        self, path: str, specification: dict, method: typing.Optional[str] = None
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

    def _iter_rules(self, rules: list[Rule]) -> typing.Generator[Rule, None, None]:
        for rule in rules:
            if hasattr(rule.target, "rules"):
                for r in self._iter_rules(rule.target.rules):
                    yield r
            else:
                yield rule

    def _application_rules(self, app: Application) -> list[Rule]:
        try:
            return list(app.default_router.rules)
        except AttributeError:
            return []

    def _rule_path(self, rule: Rule) -> str:
        matcher = getattr(rule, "matcher", None)
        regex = getattr(matcher, "regex", None)
        pattern = getattr(regex, "pattern", "")
        return pattern[:-1] if pattern.endswith("$") else pattern


Extension = Apiman
