"""OpenAPI3 example
"""
from functools import partial

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.endpoints import HTTPEndpoint
from uvicorn import run
from openapi_spec_validator import validate_v3_spec
from starlette.testclient import TestClient

from starchart.generators import SchemaGenerator
from starchart.endpoints import SwaggerUI, RedocUI, Schema


app = Starlette(debug=True)

app.schema_generator = SchemaGenerator(
    title="Dog store",
    description="Dog store api document",
    version="0.1",
    openapi_version="3.0.0",
)
# define data
DOGS = {1: {"id": 1, "name": "Ping", "age": 2}, 2: {"id": 2, "name": "Pong", "age": 1}}
# add schema
app.schema_generator.add_schema(
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
@app.route("/dog/")
class Dog(HTTPEndpoint):
    def get(self, req: Request):
        """
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
        return JSONResponse(DOGS[1])

    def delete(self, req: Request):
        """
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
        return JSONResponse(dog)


# define doc by yaml or json file
@app.route("/dogs/", methods=["GET"])
@app.schema_generator.schema_from("./examples/docs/dogs_get.yml")
def list_dogs(req: Request):
    return JSONResponse(list(DOGS.values()))


@app.route("/dogs/", methods=["POST"])
@app.schema_generator.schema_from("./examples/docs/dogs_post.json")
async def list_dogs(req: Request):
    dog = await req.json()
    DOGS[dog["id"]] = dog
    return JSONResponse(dog)


# add document's endpoints
schema_path = "/docs/schema/"
app.add_route(
    "/docs/swagger/",
    SwaggerUI,
    methods=["GET"],
    name="SwaggerUI",
    include_in_schema=False,
)
app.add_route(
    "/docs/redoc/", RedocUI, methods=["GET"], name="SwaggerUI", include_in_schema=False
)
app.add_route(
    schema_path, Schema, methods=["GET"], name="SwaggerSchema", include_in_schema=False
)
# config endpoints
SwaggerUI.set_schema_url(schema_path)
RedocUI.set_schema_url(schema_path)
SwaggerUI.set_title("Cat store")
RedocUI.set_title("Cat store")
Schema.set_schema_loader(partial(app.schema_generator.get_schema, app.routes))


def test_app():
    client = TestClient(app)
    validate_v3_spec(app.schema)
    assert client.get(schema_path).json() == app.schema
    assert client.get("/docs/swagger/").status_code == 200
    assert client.get("/docs/redoc/").status_code == 200


if __name__ == "__main__":
    run(app)
