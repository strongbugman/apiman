"""OpenAPI3 example
"""
import asyncio

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.endpoints import HTTPEndpoint
from uvicorn import run
from openapi_spec_validator import validate_v3_spec
from starlette.testclient import TestClient

from starchart import Starchart


app = Starlette(debug=True)

starchart = Starchart(
    title="Dog store",
    description="Dog store api document",
    version="0.1",
    openapi_version="3.0.0",
)
starchart.register(app)

# define data
DOGS = {1: {"id": 1, "name": "Ping", "age": 2}, 2: {"id": 2, "name": "Pong", "age": 1}}
# add schema
starchart.schema_generator.add_schema(
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
@starchart.schema_generator.schema_from("./examples/docs/dogs_get.yml")
def list_dogs(req: Request):
    return JSONResponse(list(DOGS.values()))


@app.route("/dogs/", methods=["POST"])
@starchart.schema_generator.schema_from("./examples/docs/dogs_post.json")
async def list_dogs(req: Request):
    dog = await req.json()
    DOGS[dog["id"]] = dog
    return JSONResponse(dog)


def test_app():
    # Trigger app start event
    asyncio.get_event_loop().run_until_complete(app.router.lifespan.startup())

    client = TestClient(app)
    schema = starchart.schema_generator.get_schema(app.routes)
    validate_v3_spec(schema)
    assert client.get("/docs/schema/").json() == schema
    assert client.get("/docs/swagger/").status_code == 200
    assert client.get("/docs/redoc/").status_code == 200


if __name__ == "__main__":
    run(app)
