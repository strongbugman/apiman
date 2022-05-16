import pytest
from bottle import app, request, route, run
from webtest import TestApp

from apiman.bottle import Apiman

apiman = Apiman()
apiman.init_app(app[0])


@route("/hello")
def hello():
    """
    get:
      summary: hello api
      responses:
        "200":
          description: OK
    """
    return "Hello World!"


@route("/validate/<path>", method="POST")
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
)
def validate(path):
    apiman.validate_request(request)
    return "OK echo"


def test_app():
    client = TestApp(app[0])
    spec = apiman.load_specification(app[0])
    apiman.validate_specification()
    assert client.get(apiman.config["specification_url"]).json == spec
    assert client.get(apiman.config["swagger_url"]).status_code == 200
    assert client.get(apiman.config["redoc_url"]).status_code == 200
    # --
    assert client.get("/hello").status_code == 200
    client.set_cookie("cookie", "test")
    assert (
        client.post_json(
            "/validate/test?query=test",
            {"id": 1, "name": "test"},
            headers={"Header": "test"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/validate/test?query=test",
            "id=1&name=test",
            headers={
                "Header": "test",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/validate/test?query=test",
            """<?xml version="1.0" encoding="UTF-8"?> <data> <id>0</id> <name>string</name> </data>""",
            headers={"Header": "test", "Content-Type": "application/xml"},
        ).status_code
        == 200
    )
    with pytest.raises(Exception):
        assert (
            client.post_json(
                "/validate/test?query=test",
                {"id": "1", "name": "test"},
                headers={"Header": "test"},
            ).status_code
            == 200
        )
    with pytest.raises(Exception):
        assert (
            client.post_json(
                "/validate/test?query=test", {"id": 1, "name": "test"}
            ).status_code
            == 200
        )
    client.reset()
    with pytest.raises(Exception):
        assert (
            client.post_json(
                "/validate/test?query=test",
                {"id": 1, "name": "test"},
                headers={"Header": "test"},
            ).status_code
            == 200
        )


if __name__ == "__main__":
    run(host="localhost", port=8080, debug=True)
