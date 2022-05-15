import json
import os
import typing

from django.conf import settings
from django.http.request import HttpRequest
from django.http.response import HttpResponse, JsonResponse
from django.urls import get_resolver
from jinja2 import Template

from .base import Apiman as _Apiman


class Apiman(_Apiman):
    """Django extension

    Set middleware in settings.py:
    >>> MIDDLEWARE = [
    ...     ...
    ...     "apiman.django.Middleware",
    ... ]
    Set config in settings.py:
    >>> APIMAN_TITLE = "OpenAPI Document"
    ... APIMNA_SPECIFICATION_URL="/apiman/specification/"
    ...

    Then in views:
    >>> from apiman.django import apiman
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
    >>> @apiman.from_file("./examples/docs/dogs_get.yml")
    ... def list_dogs(req):
    ...     return JsonRespons(list(DOGS.values()))
    """

    def __init__(
        self,
        title="OpenAPI Document",
        specification_url="/apiman/specification/",
        swagger_url="/apiman/swagger/",
        redoc_url="/apiman/redoc/",
        swagger_template=os.path.join(_Apiman.STATIC_DIR, "swagger.html"),
        redoc_template=os.path.join(_Apiman.STATIC_DIR, "redoc.html"),
        template=os.path.join(_Apiman.STATIC_DIR, "template.yaml"),
    ):
        super().__init__(
            title=title,
            specification_url=specification_url,
            swagger_url=swagger_url,
            redoc_url=redoc_url,
            swagger_template=swagger_template,
            redoc_template=redoc_template,
            template=template,
        )
        self.views: typing.Dict[str, typing.Callable] = {}

    def init_app(self):
        for key in (
            "title",
            "specification_url",
            "swagger_url",
            "redoc_url",
            "swagger_template",
            "redoc_template",
            "template",
        ):
            k = f"APIMAN_{key.upper()}"
            if hasattr(settings, k):
                setattr(self, key, getattr(settings, k))

        if self.swagger_template and self.swagger_url:
            swagger_html = Template(open(self.swagger_template).read()).render(
                self.config
            )
            self.route(
                self.swagger_url,
                lambda: HttpResponse(swagger_html),
            )
        if self.redoc_template and self.redoc_template:
            redoc_html = Template(open(self.redoc_template).read()).render(self.config)
            self.route(self.redoc_url, lambda: HttpResponse(redoc_html))
        if self.specification_url:
            self.route(
                self.specification_url,
                lambda: JsonResponse(self.load_specification(None)),
            )

    def get_request_schema(self, request: HttpRequest) -> typing.Dict:
        return self._get_path_schema(
            "/" + self._covert_path_rule(request.resolver_match.route),
            request.method.lower(),
        )

    def get_request_data(self, request: HttpRequest, k: str) -> typing.Any:
        if k == "query":
            return dict(request.GET.items())
        elif k == "path":
            return dict(request.resolver_match.kwargs)
        elif k == "cookie":
            return dict(request.COOKIES)
        elif k == "header":
            return dict(request.headers)
        elif k == "json":
            return json.loads(request.body)
        elif k == "form":
            return dict(request.POST)
        elif k == "xml":
            return self.xmltodict(request.body)
        else:
            return {}

    def _load_pattern_specification(self, pattern, base_path: str = "/"):
        if hasattr(pattern, "url_patterns"):
            for p in pattern.url_patterns:
                self._load_pattern_specification(
                    p, base_path=base_path + getattr(pattern.pattern, "_route", "")
                )
        else:
            if not hasattr(pattern.pattern, "_route"):
                return
            path = base_path + pattern.pattern._route
            func = pattern.callback
            if hasattr(func, "view_class"):  # view class
                # from class
                specification = self.parse(func.view_class)  # type: ignore
                self.add_path(path, specification)
                # from class methods
                for method in self.HTTP_METHODS:
                    _func = getattr(func.view_class, method, None)  # type: ignore
                    if _func:
                        specification = self.parse(_func)
                        if specification:
                            self.add_path(path, specification, method=method)
            else:  # view function
                specification = self.parse(func)
                if specification and (
                    set(specification.keys()) & self.HTTP_METHODS
                ):  # multi method description
                    self.add_path(path, specification)

    def load_specification(self, _) -> typing.Dict:
        if not self.loaded:
            self._load_pattern_specification(get_resolver())
            return self._load_specification()
        else:
            return self.specification

    def route(self, url: str, func):
        self.views[url] = func

    def add_path(
        self, path: str, specification: typing.Dict, method: typing.Optional[str] = None
    ):
        return super().add_path(
            self._covert_path_rule(path), specification, method=method
        )

    def _covert_path_rule(self, path: str) -> str:
        # covert django variable rules, eg "/path/<int:id>" to "/path/{id}"
        _subs = []
        for _sub in path.split("/"):
            if _sub.startswith("<") and _sub.endswith(">"):
                _subs.append(f"{{{_sub[1:-1].split(':')[-1]}}}")
            else:
                _subs.append(_sub)

        return "/".join(_subs)


apiman = Apiman()
apiman.init_app()


class Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        apiman.load_specification(None)
        url = request.get_full_path()
        if url in apiman.views:
            return apiman.views[url]()

        else:
            return self.get_response(request)


Extension = Apiman
