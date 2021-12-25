"""OpenAPI3 with flask
"""
import pytest
from flask import Flask, Response, jsonify, request
from flask.views import MethodView
from openapi_spec_validator import validate_v3_spec

from apiman.flask import Extension

app = Flask(__name__)
openapi = Extension(
    template="./examples/docs/dog_template.yml", decorators=(lambda f: f,)
)
openapi.init_app(app)

# define data
DOGS = {1: {"id": 1, "name": "Ping", "age": 2}, 2: {"id": 2, "name": "Pong", "age": 1}}
# add schema
openapi.add_schema(
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
@openapi.from_dict(
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
                        }
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
        openapi.validate_request(request)
        return jsonify(DOGS[id])

    @openapi.from_yaml(
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
@openapi.from_file("./examples/docs/dogs_get.yml")
def list_dogs():
    return jsonify(list(DOGS.values()))


@app.route("/dogs/", methods=["POST"])
@openapi.from_file("./examples/docs/dogs_post.json")
def create_dog():
    openapi.validate_request(request)
    dog = request.json
    DOGS[dog["id"]] = dog
    return jsonify(dog)


def test_app():
    client = app.test_client()
    spec = openapi.load_specification(app)
    validate_v3_spec(spec)
    assert client.get(openapi.config["specification_url"]).json == spec
    assert client.get(openapi.config["swagger_url"]).status_code == 200
    assert client.get(openapi.config["redoc_url"]).status_code == 200
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
    assert (
        client.post("/dogs/", json={"id": 1, "name": "doge", "age": 3}).status_code
        == 200
    )


if __name__ == "__main__":
    app.run(debug=True)
