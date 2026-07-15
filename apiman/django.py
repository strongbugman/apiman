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
        self.views: dict[str, typing.Callable] = {}
        self._django_initialized = False

    def init_app(self):
        if not settings.configured:
            return
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
        if self.redoc_template and self.redoc_url:
            redoc_html = Template(open(self.redoc_template).read()).render(self.config)
            self.route(self.redoc_url, lambda: HttpResponse(redoc_html))
        if self.specification_url:
            self.route(
                self.specification_url,
                lambda: JsonResponse(self.load_specification(None)),
            )
        self._django_initialized = True

    def get_request_schema(self, request: HttpRequest) -> dict:
        if not request.resolver_match:
            return {}
        return self._get_path_schema(
            "/"
            + self._covert_path_rule(
                self._normalize_route(request.resolver_match.route)
            ),
            request.method.lower(),
        )

    def get_request_data(self, request: HttpRequest, k: str) -> typing.Any:
        if k == "query":
            return {
                key: values if len(values) > 1 else values[0]
                for key, values in request.GET.lists()
            }
        elif k == "path":
            return dict(request.resolver_match.kwargs)
        elif k == "cookie":
            return dict(request.COOKIES)
        elif k == "header":
            return {key.lower(): value for key, value in request.headers.items()}
        elif k == "json":
            return self.json_loads(request.body)
        elif k == "form":
            return {
                key: values if len(values) > 1 else values[0]
                for key, values in request.POST.lists()
            }
        elif k == "xml":
            return self.xmltodict(request.body)
        else:
            return {}

    def has_request_body(self, request: HttpRequest, location: str) -> bool:
        _ = location
        content_length = request.META.get("CONTENT_LENGTH")
        if content_length:
            try:
                return int(content_length) > 0
            except ValueError:
                pass
        return bool(getattr(request, "_body", b""))

    def _load_pattern_specification(self, pattern, base_path: str = "/"):
        if hasattr(pattern, "url_patterns"):
            for p in pattern.url_patterns:
                self._load_pattern_specification(
                    p, base_path=base_path + self._route_pattern(pattern)
                )
        else:
            route_pattern = self._route_pattern(pattern)
            if not route_pattern:
                return
            path = base_path + route_pattern
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
                elif specification:
                    for method in self.HTTP_METHODS:
                        self.add_path(path, specification, method=method)

    def load_specification(self, _: typing.Any = None) -> dict:
        if not settings.configured:
            return self.specification
        if not self.loaded:
            # get_resolver() wraps the whole URLconf in an implicit root
            # URLResolver whose own pattern ("^/") is Django-internal
            # boilerplate, not a real path segment -- Django's own
            # resolver_match.route never includes it. Walk its direct
            # url_patterns instead of the resolver itself so that
            # contribution is never added to any registered path.
            for p in get_resolver().url_patterns:
                self._load_pattern_specification(p)
            return self._load_specification()
        else:
            return self.specification

    def route(self, url: str, func):
        self.views[url] = func

    def add_path(
        self, path: str, specification: dict, method: typing.Optional[str] = None
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

    def _route_pattern(self, pattern) -> str:
        route_pattern = getattr(getattr(pattern, "pattern", None), "_route", None)
        if route_pattern is not None:
            return route_pattern
        # re_path()-based RegexPattern has no "_route"; its raw regex text
        # keeps its own leading "^", which Django's own route-joining
        # (URLResolver._join_route) strips from each nested child before
        # concatenating. Mirror that here so registered paths match what
        # request.resolver_match.route actually looks like at request time.
        return self._normalize_route(str(getattr(pattern, "pattern", "")))

    def _normalize_route(self, route: str) -> str:
        # e.g. "^api/items/(?P<id>\\d+)/$" -> "api/items/(?P<id>\\d+)/$"
        return route[1:] if route.startswith("^") else route


apiman = Apiman()
if settings.configured:
    apiman.init_app()


class Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        if not apiman._django_initialized:
            apiman.init_app()
        apiman.load_specification(None)
        url = request.get_full_path()
        if url in apiman.views:
            return apiman.views[url]()

        else:
            return self.get_response(request)


Extension = Apiman
