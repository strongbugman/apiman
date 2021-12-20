"""OpenAPI2(Swagger) with Starlette
"""
import pytest
from openapi_spec_validator import validate_v2_spec
from starlette.applications import Starlette
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient
from uvicorn import run

from apiman.starlette import Extension

app = Starlette()
sub_app = Starlette()
openapi = Extension(
    template="./examples/docs/cat_template.yml", decorators=(lambda f: f,)
)
openapi.init_app(app)


# define data
CATS = {
    1: {"id": 1, "name": "DangDang", "age": 2},
    2: {"id": 2, "name": "DingDing", "age": 1},
}
# add schema definition
openapi.add_schema("cat_age", {"type": "integer", "minimum": 0, "maximum": 3000})
openapi.add_schema(
    "Cat",
    {
        "properties": {
            "id": {"description": "global unique", "type": "integer"},
            "name": {"type": "string"},
            "age": {"$ref": "#/definitions/cat_age"},
        },
        "type": "object",
    },
)


# define routes and schema(in doc string)
@app.route("/cat/{id}/")
class Cat(HTTPEndpoint):
    """
    Declare multi method
    ---
    get:
      summary: Get single cat
      tags:
      - cat
      parameters:
      - name: id
        type: string
        in: path
        required: True
      - name: test_param1
        type: string
        in: header
        required: True
      - name: test_param2
        type: string
        in: query
        required: True
      responses:
        "200":
          description: OK
          schema:
            $ref: '#/definitions/Cat'
        "404":
          description: Not found
    """

    def get(self, req: Request):
        openapi.validate_request(req)
        return JSONResponse(CATS[int(req.path_params["id"])])

    def delete(self, req: Request):
        """
        Declare single method
        ---
        summary: Delete single cat
        tags:
        - cat
        parameters:
        - name: id
          type: integer
          in: path
          required: True
        responses:
          "204":
            description: OK
            schema:
              $ref: '#/definitions/Cat'
          "404":
            description: Not found
        """
        cat = CATS.pop(int(req.path_params["id"]))
        return JSONResponse(cat)


# define doc by yaml or json file
@sub_app.route("/cats/", methods=["GET"])
@openapi.from_file("./examples/docs/cats_get.yml")
def list_cats(req: Request):
    return JSONResponse(list(CATS.values()))


@sub_app.route("/cats/", methods=["POST"])
@openapi.from_file("./examples/docs/cats_post.json")
async def create_cat(req: Request):
    await req.json()
    openapi.validate_request(req)
    cat = await req.json()
    CATS[cat["id"]] = cat
    return JSONResponse(cat)


app.mount("/", sub_app)


def test_app():
    client = TestClient(app)
    spec = openapi.load_specification(app)
    validate_v2_spec(spec)
    assert client.get(openapi.config["specification_url"]).json() == spec
    assert client.get(openapi.config["swagger_url"]).status_code == 200
    assert client.get(openapi.config["redoc_url"]).status_code == 200
    # --
    with pytest.raises(Exception):
        client.get("/cat/1/")
    with pytest.raises(Exception):
        client.get("/cat/1/?test_param2=test")
    assert (
        client.get(
            "/cat/1/?test_param2=test", headers={"test_param1": "test"}
        ).status_code
        == 200
    )
    # --
    with pytest.raises(Exception):
        client.post("/cats/", json={"name": "test", "id": 3})
    assert (
        client.post("/cats/", json={"name": "test", "id": 3, "age": 4}).status_code
        == 200
    )


if __name__ == "__main__":
    run(app)
