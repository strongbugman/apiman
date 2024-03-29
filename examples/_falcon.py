import falcon
import pytest
from falcon import App as WSGIApp
from falcon import Request, Response, testing
from falcon.asgi import App
from uvicorn import run

from apiman.falcon import Apiman

app = App()
apiman = Apiman()
apiman.init_app(app)

wsgi_app = WSGIApp()
wsgi_apiman = Apiman()
wsgi_apiman.init_app(wsgi_app)


class ThingsResource:
    async def on_get(self, req: Request, resp: Response, name):
        """
        summary: hello api
        parameters:
        - name: name
          in: path
          required: True
          schema:
            type: string
            default: test
        responses:
          "200":
            description: OK
        """
        apiman.validate_request(req)
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = "hi\n"


class WSGIThingsResource:
    def on_get(self, req: Request, resp: Response, name):
        """
        summary: hello api
        parameters:
        - name: name
          in: path
          required: True
          schema:
            type: string
            default: test
        responses:
          "200":
            description: OK
        """
        apiman.validate_request(req)
        resp.status = falcon.HTTP_200
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = "hi\n"


class ValidationResource:
    """
    post:
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
      - name: header
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
            application/xml:
              schema:
                xml:
                  name: 'data'
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                required:
                - id
                - name
            application/x-www-form-urlencoded:
              schema:
                type: object
                properties:
                  id:
                    type: string
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

    async def on_post(self, req: Request, resp: Response, path):
        await apiman.async_validate_request(req)
        resp.status = falcon.HTTP_200


class WSGIValidationResource:
    """
    post:
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
      - name: header
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
            application/xml:
              schema:
                xml:
                  name: 'data'
                type: object
                properties:
                  id:
                    type: string
                  name:
                    type: string
                required:
                - id
                - name
            application/x-www-form-urlencoded:
              schema:
                type: object
                properties:
                  id:
                    type: string
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

    def on_post(self, req: Request, resp: Response, path):
        for k in list(req.headers.keys()):
            req.headers[k.lower()] = req.headers[k]
        apiman.validate_request(req, ignore=["header"])
        resp.status = falcon.HTTP_200


app.add_route("/echo/{name}", ThingsResource())
app.add_route("/validate/{path}", ValidationResource())
wsgi_app.add_route("/echo/{name}", WSGIThingsResource())
wsgi_app.add_route("/validate/{path}", WSGIValidationResource())


def test_app():
    apiman.validate_specification()
    wsgi_apiman.validate_specification()
    asgi_client = testing.TestClient(app)
    wsgi_client = testing.TestClient(wsgi_app)

    # TODO: seams like asgi client need asyncio runtime(client conductor)
    for client in (wsgi_client,):
        assert client.simulate_get(apiman.specification_url).status_code == 200
        assert client.simulate_get(apiman.swagger_url).status_code == 200
        assert client.simulate_get(apiman.redoc_url).status_code == 200
        assert client.simulate_get("/echo/hi").status_code == 200
        assert (
            client.simulate_post(
                "/validate/test?query=test",
                body='{"id": 1, "name": "test"}',
                headers={
                    "content-type": "application/json",
                    "header": "test",
                    "cookie": "cookie=test",
                },
            ).status_code
            == 200
        )
        assert (
            client.simulate_post(
                "/validate/test?query=test",
                body="id=1&name=test",
                headers={
                    "content-type": "application/x-www-form-urlencoded",
                    "header": "test",
                    "cookie": "cookie=test",
                },
            ).status_code
            == 200
        )
        # no default xml handler
        # assert client.simulate_post('/validate/test?query=test', body="""<?xml version="1.0" encoding="UTF-8"?> <data> <id>0</id> <name>string</name> </data>""", headers={"content-type": "application/xml", "header": "test", "cookie": "cookie=test"}).status_code == 200

        if client is asgi_client:
            with pytest.raises(Exception):
                assert (
                    client.simulate_post(
                        "/validate/test?query=test",
                        body='{"id": 1, "name": "test"}',
                        headers={
                            "content-type": "application/json",
                            "heade": "test",
                            "cookie": "cookie=test",
                        },
                    ).status_code
                    == 200
                )
        else:
            assert (
                client.simulate_post(
                    "/validate/test?query=test",
                    body='{"id": 1, "name": "test"}',
                    headers={
                        "content-type": "application/json",
                        "heade": "test",
                        "cookie": "cookie=test",
                    },
                ).status_code
                == 200
            )
        with pytest.raises(Exception):
            assert (
                client.simulate_post(
                    "/validate/test?query=test",
                    body='{"id": "0", "name": "test"}',
                    headers={
                        "content-type": "application/json",
                        "header": "test",
                        "cookie": "cookie=test",
                    },
                ).status_code
                == 200
            )


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.DEBUG)
    # from wsgiref.simple_server import make_server
    # with make_server('', 8000, wsgi_app) as httpd:
    #     logging.info("Serving on port 8000...")
    #     httpd.serve_forever()
    run(app)
