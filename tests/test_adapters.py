from __future__ import annotations

import asyncio
import types

import pytest
from bottle import Bottle
from bottle import request as bottle_request
from falcon import App as FalconApp
from falcon import testing as falcon_testing
from flask import Flask
from flask import request as flask_request
from starlette.applications import Starlette
from starlette.requests import Request as StarletteRequest
from tornado.web import Application as TornadoApplication
from werkzeug.test import EnvironBuilder

from apiman.bottle import Apiman as BottleApiman
from apiman.django import Apiman as DjangoApiman
from apiman.falcon import Apiman as FalconApiman
from apiman.flask import Apiman as FlaskApiman
from apiman.starlette import Apiman as StarletteApiman
from apiman.tornado import Apiman as TornadoApiman


def test_falcon_wsgi_content_type_is_detected_case_insensitively() -> None:
    app = FalconApp()
    apiman = FalconApiman()
    apiman.init_app(app)
    apiman.add_path(
        "/items",
        {
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {"a": {"type": "string"}},
                            "required": ["a"],
                        }
                    }
                },
            },
            "responses": {"200": {"description": "OK"}},
        },
        method="post",
    )

    class ItemsResource:
        def on_post(self, req, resp):
            # No manual header-lowering workaround needed anymore.
            apiman.validate_request(req)
            resp.status = "200 OK"

    app.add_route("/items", ItemsResource())
    client = falcon_testing.TestClient(app)
    result = client.simulate_post(
        "/items",
        body='{"a": "x"}',
        headers={"Content-Type": "application/json"},
    )
    assert result.status_code == 200


@pytest.mark.parametrize(
    "make_apiman_and_app",
    [
        lambda: (DjangoApiman(), None),
        lambda: (FalconApiman(), FalconApp()),
        lambda: (FlaskApiman(), Flask(__name__)),
        lambda: (BottleApiman(), Bottle()),
        lambda: (TornadoApiman(), TornadoApplication()),
        lambda: (StarletteApiman(), Starlette()),
    ],
    ids=["django", "falcon", "flask", "bottle", "tornado", "starlette"],
)
def test_reload_with_no_arguments_does_not_crash_after_init_app(
    make_apiman_and_app,
) -> None:
    apiman, app = make_apiman_and_app()
    if app is not None:
        apiman.init_app(app)

    # Documented as `apiman.reload(...)` — must be safe to call with no args
    # once the adapter is wired up via init_app.
    apiman.reload()


def test_starlette_sync_get_request_data_raises_clear_error_when_body_unread() -> None:
    apiman = StarletteApiman()
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"content-type", b"application/json")],
        "query_string": b"",
    }

    async def receive():
        return {"type": "http.request", "body": b'{"a": 1}', "more_body": False}

    request = StarletteRequest(scope, receive)

    with pytest.raises(RuntimeError):
        apiman.get_request_data(request, "json")


def test_starlette_async_get_request_data_returns_body_once_awaited() -> None:
    apiman = StarletteApiman()
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"content-type", b"application/json")],
        "query_string": b"",
    }

    async def receive():
        return {"type": "http.request", "body": b'{"a": 1}', "more_body": False}

    request = StarletteRequest(scope, receive)

    async def run():
        return await apiman.async_get_request_data(request, "json")

    assert asyncio.run(run()) == {"a": 1}


def test_starlette_repeated_form_values_are_preserved_as_list() -> None:
    apiman = StarletteApiman()
    body = b"tags=red&tags=blue"
    sent = False
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "headers": [
            (b"content-type", b"application/x-www-form-urlencoded"),
            (b"content-length", str(len(body)).encode()),
        ],
        "query_string": b"",
        "client": ("test", 1),
        "server": ("test", 80),
    }

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    request = StarletteRequest(scope, receive)

    async def run():
        return await apiman.async_get_request_data(request, "form")

    assert asyncio.run(run()) == {"tags": ["red", "blue"]}


def test_flask_repeated_form_values_are_preserved_as_list() -> None:
    app = Flask(__name__)
    apiman = FlaskApiman()
    captured: dict = {}

    @app.route("/form", methods=["POST"])
    def form_endpoint():
        captured["data"] = apiman.get_request_data(flask_request, "form")
        return ""

    client = app.test_client()
    client.post("/form", data={"tags": ["red", "blue"]})
    assert captured["data"]["tags"] == ["red", "blue"]


def test_bottle_repeated_form_values_are_preserved_as_list() -> None:
    app = Bottle()
    apiman = BottleApiman()
    captured: dict = {}

    @app.route("/form", method="POST")
    def form_endpoint():
        captured["data"] = apiman.get_request_data(bottle_request, "form")
        return ""

    builder = EnvironBuilder(
        method="POST", path="/form", data={"tags": ["red", "blue"]}
    )
    env = builder.get_environ()

    def start_response(status, headers):
        pass

    list(app(env, start_response))
    assert captured["data"]["tags"] == ["red", "blue"]


def test_django_nested_re_path_uses_the_runtime_resolver_key() -> None:
    from django.http import HttpResponse
    from django.urls import include, re_path, resolve

    def view(request, item_id):
        _ = request, item_id
        return HttpResponse("ok")

    view.__doc__ = """summary: item
parameters:
- name: item_id
  in: path
  required: true
  schema:
    type: string
responses:
  "200":
    description: OK
"""
    child_patterns = [re_path(r"^items/(?P<item_id>\d+)/$", view)]
    urlconf = types.ModuleType("apiman_test_nested_urls")
    urlconf.urlpatterns = [re_path(r"^api/", include((child_patterns, "child")))]

    apiman = DjangoApiman()
    for pattern in urlconf.urlpatterns:
        apiman._load_pattern_specification(pattern)
    apiman._load_specification()
    match = resolve("/api/items/7/", urlconf=urlconf)
    request_key = "/" + apiman._covert_path_rule(apiman._normalize_route(match.route))
    request = types.SimpleNamespace(resolver_match=match, method="GET")

    assert request_key in apiman.specification["paths"]
    assert apiman.get_request_schema(request)["path"]
