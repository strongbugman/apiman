"""OpenAPI3 with flask
"""
from flask import Flask, jsonify, request
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
    },
)


# define routes and schema(in doc string)
class DogView(MethodView):
    """
    Declare multi method
    ---
    get:
      summary: Get single dog
      tags:
      - dog
      parameters:
      - name: id
        in: query
        required: True
        schema:
          type: integer
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Dog'
        "404":
          description: Not found
    """
    def get(self):
        return jsonify(DOGS[1])

    def delete(self):
        """
        Declare single method
        ---
        summary: Delete single dog
        tags:
        - dog
        parameters:
        - name: id
          in: query
          required: True
          schema:
            type: integer
        responses:
          "204":
            description: OK
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/Dog'
          "404":
            description: Not found
        """
        dog = DOGS.pop(1)
        return jsonify(dog)


app.add_url_rule("/dog/", view_func=DogView.as_view(name="dog"))


# define doc by yaml or json file
@app.route("/dogs/", methods=["GET"])
@openapi.from_file("./examples/docs/dogs_get.yml")
def list_dogs():
    return jsonify(list(DOGS.values()))


@app.route("/dogs/", methods=["POST"])
@openapi.from_file("./examples/docs/dogs_post.json")
def create_dog():
    dog = request.json()
    DOGS[dog["id"]] = dog
    return jsonify(dog)


def test_app():
    client = app.test_client()
    spec = openapi.load_specification(app)
    validate_v3_spec(spec)
    assert client.get(openapi.config["specification_url"]).json == spec
    assert client.get(openapi.config["swagger_url"]).status_code == 200
    assert client.get(openapi.config["redoc_url"]).status_code == 200


if __name__ == "__main__":
    app.run(debug=True)
