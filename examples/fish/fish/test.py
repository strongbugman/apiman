import json

from apiman.django import openapi
from django.test import TestCase
from jsonschema_rs import ValidationError
from openapi_spec_validator import validate_v3_spec


class MyTestCase(TestCase):
    def test_api(self):
        self.assertEqual(self.client.get("/apiman/swagger/").status_code, 200)
        self.assertEqual(self.client.get("/apiman/redoc/").status_code, 200)
        self.assertEqual(self.client.get("/apiman/specification/").status_code, 200)
        validate_v3_spec(openapi.specification)

    def test_validate(self):
        self.assertEqual(self.client.get("/health/hello/").status_code, 200)
        self.assertEqual(self.client.get("/fishes/?id=1").status_code, 200)
        self.client.cookies["x-test"] = "1"
        self.client.post(
            "/fishes/",
            json.dumps({"id": 2, "name": "w", "age": 0}),
            content_type="application/json",
            **{"HTTP_X-Theader": "t"}
        )

        # query
        with self.assertRaises(ValidationError):
            self.client.get("/fishes/")
        # header
        with self.assertRaises(ValidationError):
            self.client.post(
                "/fishes/",
                json.dumps({"id": 2, "name": "w", "age": 0}),
                content_type="application/json",
            )
        # json
        with self.assertRaises(ValidationError):
            self.client.post(
                "/fishes/",
                json.dumps({"id": 2, "name": "w", "age": "0"}),
                content_type="application/json",
                **{"HTTP_X-Theader": "t"}
            )
        # cookie
        with self.assertRaises(ValidationError):
            self.client.cookies.pop("x-test")
            self.client.post(
                "/fishes/",
                json.dumps({"id": 2, "name": "w", "age": 0}),
                content_type="application/json",
                **{"HTTP_X-Theader": "t"}
            )
