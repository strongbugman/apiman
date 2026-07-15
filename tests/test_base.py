from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import jsonschema_rs
import pytest

from apiman.base import Apiman as BaseApiman


@dataclass
class Request:
    path: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)


class Apiman(BaseApiman):
    def get_request_schema(self, request: Request) -> dict[str, Any]:
        return self._get_path_schema(request.path, request.method.lower())

    def get_request_data(self, request: Request, k: str) -> Any:
        return request.data.get(k)

    def get_request_content_type(self, request: Request) -> str:
        return request.headers.get("content-type", "")


def _base_spec(version: str) -> dict[str, Any]:
    if version == "2.0":
        return {
            "swagger": "2.0",
            "info": {"title": "API", "version": "1.0"},
            "paths": {
                "/ping": {
                    "get": {
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
        }
    return {
        "openapi": version,
        "info": {"title": "API", "version": "1.0"},
        "paths": {
            "/ping": {
                "get": {
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }


@pytest.mark.parametrize("version", ["2.0", "3.0.3", "3.1.0"])
def test_validate_specification_accepts_supported_versions(version: str) -> None:
    apiman = Apiman()
    apiman.specification = _base_spec(version)

    apiman.validate_specification()


@pytest.mark.parametrize(
    "specification",
    [
        {"swagger": "2.0", "paths": {}},
        {"openapi": "3.0.3", "paths": {}},
        {"openapi": "3.1.0", "paths": {}},
    ],
)
def test_validate_specification_rejects_invalid_documents(
    specification: dict[str, Any],
) -> None:
    apiman = Apiman()
    apiman.specification = specification

    with pytest.raises(jsonschema_rs.ValidationError):
        apiman.validate_specification()


def test_openapi30_validation_rejects_parameter_with_schema_and_content() -> None:
    apiman = Apiman()
    apiman.specification = {
        "openapi": "3.0.3",
        "info": {"title": "API", "version": "1.0"},
        "paths": {
            "/items": {
                "get": {
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "schema": {"type": "string"},
                            "content": {
                                "application/json": {
                                    "schema": {"type": "string"},
                                }
                            },
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    with pytest.raises(jsonschema_rs.ValidationError):
        apiman.validate_specification()


def test_header_parameters_are_case_insensitive() -> None:
    apiman = Apiman()
    apiman.add_path(
        "/items",
        {
            "parameters": [
                {
                    "name": "X-Token",
                    "in": "header",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
            "responses": {"200": {"description": "OK"}},
        },
        method="get",
    )

    for header_name in ("x-token", "X-Token", "X-TOKEN"):
        apiman.validate_request(
            Request(
                "/items",
                headers={header_name: "secret"},
                data={"header": {header_name: "secret"}},
            )
        )


def test_non_header_parameter_names_remain_case_sensitive() -> None:
    apiman = Apiman()
    apiman.add_path(
        "/items",
        {
            "parameters": [
                {
                    "name": "Name",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
            "responses": {"200": {"description": "OK"}},
        },
        method="get",
    )

    with pytest.raises(jsonschema_rs.ValidationError):
        apiman.validate_request(Request("/items", data={"query": {"name": "wrong"}}))


def test_add_path_invalidates_cached_path_schema() -> None:
    apiman = Apiman()
    assert "query" in apiman.get_request_schema(Request("/late"))

    apiman.add_path(
        "/late",
        {
            "parameters": [
                {
                    "name": "required",
                    "in": "query",
                    "required": True,
                    "schema": {"type": "string"},
                }
            ],
            "responses": {"200": {"description": "OK"}},
        },
        method="get",
    )

    with pytest.raises(jsonschema_rs.ValidationError):
        apiman.validate_request(Request("/late", data={"query": {}}))


def test_reset_and_reload_clear_loaded_state_and_schema_cache() -> None:
    class ReloadingApiman(Apiman):
        def load_specification(self, marker: str) -> dict[str, Any]:
            self.specification["x-marker"] = marker
            return self._load_specification()

    apiman = ReloadingApiman()
    apiman.loaded = True
    apiman._path_schemas["stale"] = {}

    specification = apiman.reload("fresh")

    assert specification["x-marker"] == "fresh"
    assert apiman.loaded is True
    assert apiman._path_schemas == {}


def test_openapi2_parameter_constraints_are_preserved() -> None:
    apiman = Apiman()
    apiman.specification = _base_spec("2.0")
    apiman.add_path(
        "/status",
        {
            "parameters": [
                {
                    "name": "code",
                    "in": "query",
                    "required": True,
                    "type": "string",
                    "pattern": "^[A-Z]+$",
                    "enum": ["OK"],
                }
            ],
            "responses": {"200": {"description": "OK"}},
        },
        method="get",
    )

    apiman.validate_request(Request("/status", data={"query": {"code": "OK"}}))
    with pytest.raises(jsonschema_rs.ValidationError):
        apiman.validate_request(Request("/status", data={"query": {"code": "bad"}}))


def test_openapi2_body_uses_declared_consumes_media_type() -> None:
    apiman = Apiman()
    apiman.specification = _base_spec("2.0")
    apiman.add_path(
        "/items",
        {
            "consumes": ["application/problem+json"],
            "parameters": [
                {
                    "name": "body",
                    "in": "body",
                    "required": True,
                    "schema": {
                        "type": "object",
                        "properties": {"title": {"type": "string"}},
                        "required": ["title"],
                    },
                }
            ],
            "responses": {"200": {"description": "OK"}},
        },
        method="post",
    )

    apiman.validate_request(
        Request(
            "/items",
            method="POST",
            headers={"content-type": "application/problem+json"},
            data={"json": {"title": "bad request"}},
        )
    )


def test_required_request_body_rejects_missing_body_even_when_schema_allows_empty() -> (
    None
):
    apiman = Apiman()
    apiman.add_path(
        "/items",
        {
            "requestBody": {
                "required": True,
                "content": {"application/json": {"schema": {}}},
            },
            "responses": {"200": {"description": "OK"}},
        },
        method="post",
    )

    with pytest.raises(jsonschema_rs.ValidationError):
        apiman.validate_request(
            Request(
                "/items",
                method="POST",
                headers={"content-type": "application/json"},
                data={"json": None},
            )
        )
    apiman.validate_request(
        Request(
            "/items",
            method="POST",
            headers={"content-type": "application/json"},
            data={"json": {}},
        )
    )


@pytest.mark.parametrize(
    "content_type",
    ["application/json; charset=utf-8", "application/problem+json"],
)
def test_json_media_type_matching_accepts_parameters_and_structured_suffixes(
    content_type: str,
) -> None:
    apiman = Apiman()
    apiman.add_path(
        "/errors",
        {
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {"title": {"type": "string"}},
                            "required": ["title"],
                        }
                    }
                },
            },
            "responses": {"200": {"description": "OK"}},
        },
        method="post",
    )

    apiman.validate_request(
        Request(
            "/errors",
            method="POST",
            headers={"content-type": content_type},
            data={"json": {"title": "bad request"}},
        )
    )


def test_repeated_query_values_support_array_parameters() -> None:
    apiman = Apiman()
    apiman.add_path(
        "/search",
        {
            "parameters": [
                {
                    "name": "tag",
                    "in": "query",
                    "schema": {"type": "array", "items": {"type": "string"}},
                }
            ],
            "responses": {"200": {"description": "OK"}},
        },
        method="get",
    )

    apiman.validate_request(
        Request("/search", data={"query": {"tag": ["red", "blue"]}})
    )
    apiman.validate_request(Request("/search", data={"query": {"tag": "red"}}))


def test_repeated_scalar_query_values_remain_invalid() -> None:
    apiman = Apiman()
    apiman.add_path(
        "/search",
        {
            "parameters": [
                {
                    "name": "tag",
                    "in": "query",
                    "schema": {"type": "string"},
                }
            ],
            "responses": {"200": {"description": "OK"}},
        },
        method="get",
    )

    with pytest.raises(jsonschema_rs.ValidationError):
        apiman.validate_request(
            Request("/search", data={"query": {"tag": ["red", "blue"]}})
        )
