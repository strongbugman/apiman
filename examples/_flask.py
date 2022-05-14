"""OpenAPI3 with flask
"""
import pytest
from flask import Flask, Response, jsonify, request
from flask.views import MethodView
from openapi_spec_validator import validate_v3_spec

from apiman.flask import Apiman

app = Flask(__name__)
apiman = Apiman(template="./examples/docs/dog_template.yml")
apiman.init_app(app)

# define data
DOGS = {1: {"id": 1, "name": "Ping", "age": 2}, 2: {"id": 2, "name": "Pong", "age": 1}}
# add schema
apiman.add_schema(
    "Dog",
    {
        "properties": {
            "id": {"description": "global unique", "type": "integer"},
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "type": "object",
        "required": ["id", "name", "age"],
    },
)


# define routes and schema(in doc string)
@apiman.from_dict(
    {
        "get": {
            "parameters": [
                {
                    "in": "path",
                    "name": "id",
                    "required": True,
                    "schema": {"type": "integer"},
                },
                {
                    "in": "query",
                    "name": "test_param1",
                    "required": True,
                    "schema": {"type": "string"},
                },
                {
                    "in": "header",
                    "name": "Test-Param2",
                    "required": True,
                    "schema": {"type": "string"},
                },
            ],
            "responses": {
                "200": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "properties": {
                                    "age": {"type": "integer"},
                                    "id": {
                                        "description": "global unique",
                                        "type": "integer",
                                    },
                                    "name": {"type": "string"},
                                },
                                "required": ["id", "name", "age"],
                                "type": "object",
                            }
                        },
                    },
                    "description": "OK",
                },
                "404": {"description": "Not found"},
            },
            "summary": "Get single dog",
            "tags": ["dog"],
        }
    }
)
class DogView(MethodView):
    def get(self, id):
        """
        Normal annotation will be ignored
        """
        apiman.validate_request(request)
        return jsonify(DOGS[id])

    @apiman.from_yaml(
        """
        summary: Delete single dog
        tags:
        - dog
        parameters:
        - name: id
          in: path
          required: True
          schema:
            type: integer
        responses:
          "204":
            description: OK
          "404":
            description: Not found
        """
    )
    def delete(self, id):
        DOGS.pop(id)
        return Response(status=204)


app.add_url_rule("/dog/<int:id>", view_func=DogView.as_view(name="dog"))


# define doc by yaml or json file
@app.route("/dogs/", methods=["GET"])
@apiman.from_file("./examples/docs/dogs_get.yml")
def list_dogs():
    return jsonify(list(DOGS.values()))


@app.route("/dogs/", methods=["POST"])
@apiman.from_file("./examples/docs/dogs_post.json")
def create_dog():
    apiman.validate_request(request)
    dog = request.json
    DOGS[dog["id"]] = dog
    return jsonify(dog)


def test_app():
    client = app.test_client()
    spec = apiman.load_specification(app)
    validate_v3_spec(spec)
    assert client.get(apiman.config["specification_url"]).json == spec
    assert client.get(apiman.config["swagger_url"]).status_code == 200
    assert client.get(apiman.config["redoc_url"]).status_code == 200
    # --
    with pytest.raises(Exception):
        assert client.get("/dog/1") == 200
    with pytest.raises(Exception):
        assert client.get("/dog/1?test_param1=test") == 200
    assert (
        client.get(
            "/dog/1?test_param1=test", headers={"test_param2": "test"}
        ).status_code
        == 200
    )
    with pytest.raises(Exception):
        assert client.post("/dogs/", json={"id": 1, "name": "doge"}).status_code == 200
    with pytest.raises(Exception):
        assert (
            client.post(
                "/dogs/",
                data="age=1&id=2&name=3",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ).status_code
            == 200
        )
    with pytest.raises(Exception):
        assert (
            client.post(
                "/dogs/",
                data="age=1&id=2&name=3",
                headers={"Content-Type": "multipart/form-data"},
            ).status_code
            == 200
        )
    with pytest.raises(Exception):
        assert (
            client.post(
                "/dogs/",
                data="""<?xml version="1.0" encoding="UTF-8"?> <data> <age>0</age> <id>0</id> <name>string</name> </data>""",
                headers={"Content-Type": "application/xml"},
            ).status_code
            == 200
        )
    assert (
        client.post("/dogs/", json={"id": 1, "name": "doge", "age": 3}).status_code
        == 200
    )


if __name__ == "__main__":
    app.run(debug=True)
