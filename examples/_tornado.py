import json

import pytest
import tornado.httpclient
import tornado.httpserver
import tornado.ioloop
import tornado.testing
import tornado.web
from openapi_spec_validator import validate_v3_spec

from apiman.tornado import Apiman

apiman = Apiman()


class MainHandler(tornado.web.RequestHandler):
    """
    get:
      summary: hello api
      parameters:
      - name: path0
        in: path
        required: True
        schema:
          type: string
          default: test
      responses:
        "200":
          description: OK
    """

    def get(self, path):
        apiman.validate_request(self)
        self.write(f"Hello, {path}")


class ValidationHandler(tornado.web.RequestHandler):
    @apiman.from_yaml(
        """
    summary: request validate
    parameters:
    - name: path
      in: path
      required: True
      schema:
        type: string
        default: test
    - name: query
      in: query
      required: True
      schema:
        type: string
        default: test
    - name: Header
      in: header
      required: True
      schema:
        type: string
        default: test
    - name: cookie
      in: cookie
      required: True
      schema:
        type: string
        default: test
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
            required:
              - id
              - name
    responses:
      "200":
        description: OK
      "400":
        description: Request Error
    """
    )
    def post(self, path):
        apiman.validate_request(self)
        self.write(f"Hello, {path}")


app = tornado.web.Application(
    [
        (r"/hello/(.*)", MainHandler),
        (r"/validate/(?P<path>.*)", ValidationHandler),
    ]
)
apiman.init_app(app)


class TestCase(tornado.testing.AsyncHTTPTestCase):
    def get_app(self):
        return app

    def test_app(self):
        spec = apiman.load_specification(app)
        validate_v3_spec(spec)
        assert json.loads(self.fetch(apiman.config["specification_url"]).body) == spec
        assert self.fetch(apiman.config["swagger_url"]).code == 200
        assert self.fetch(apiman.config["redoc_url"]).code == 200
        assert self.fetch("/hello/test").code == 200
        # validation
        assert (
            self.fetch(
                "/validate/test?query=test",
                method="POST",
                body=json.dumps({"id": 1, "name": "test"}),
                headers={"Header": "test", "Cookie": "cookie=test"},
            ).code
            == 200
        )
        with pytest.raises(Exception):
            assert (
                self.fetch(
                    "/validate/test",
                    method="POST",
                    body=json.dumps({"id": 1, "name": "test"}),
                    headers={"Header": "test", "Cookie": "cookie=test"},
                ).code
                == 200
            )
        with pytest.raises(Exception):
            assert (
                self.fetch(
                    "/validate/test?query=test",
                    method="POST",
                    body=json.dumps({"id": "1", "name": "test"}),
                    headers={"Header": "test", "Cookie": "cookie=test"},
                ).code
                == 200
            )
        with pytest.raises(Exception):
            assert (
                self.fetch(
                    "/validate/test?query=test",
                    method="POST",
                    body=json.dumps({"id": 1, "name": "test"}),
                    headers={"Header1": "test", "Cookie": "cookie=test"},
                ).code
                == 200
            )
        with pytest.raises(Exception):
            assert (
                self.fetch(
                    "/validate/test?query=test",
                    method="POST",
                    body=json.dumps({"id": 1, "name": "test"}),
                    headers={"Header": "test", "Cookie": "cookie1=test"},
                ).code
                == 200
            )


if __name__ == "__main__":
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
