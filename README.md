# APIMAN

[![Build](https://travis-ci.com/strongbugman/apiman.svg?branch=master)](https://travis-ci.com/strongbugman/apiman)
[![codecov](https://codecov.io/gh/strongbugman/apiman/branch/master/graph/badge.svg)](https://codecov.io/gh/strongbugman/apiman)

APIMAN provide a easy way to integrate api manual/document for your web project

## Features

* Support OpenAPI 2 and 3 specification, define API specification by file or doc
* Provide configurable [SwaggerUI](http://swagger.io/swagger-ui/) and [RedocUI](https://rebilly.github.io/ReDoc/)
* Outbox extension for flask and Starlette

## Install

```shell
pip install -U apiman
```

## Examples

Let's see a Starlette example app:

```python
"""OpenAPI2(Swagger) with Starlette
"""
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.endpoints import HTTPEndpoint
from uvicorn import run
from openapi_spec_validator import validate_v2_spec
from starlette.testclient import TestClient

from apiman.starlette import Extension


app = Starlette()
openapi = Extension(template="./examples/docs/cat_template.yml")
openapi.init_app(app)


# define data
CATS = {
    1: {"id": 1, "name": "DangDang", "age": 2},
    2: {"id": 2, "name": "DingDing", "age": 1},
}
# add schema definition
openapi.add_schema(
    "Cat",
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
@app.route("/cat/")
class Cat(HTTPEndpoint):
    def get(self, req: Request):
        """
        summary: Get single cat
        tags:
        - cat
        parameters:
        - name: id
          type: integer
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
        return JSONResponse(CATS[1])

    def delete(self, req: Request):
        """
        summary: Delete single cat
        tags:
        - cat
        parameters:
        - name: id
          type: integer
          in: query
          required: True
        responses:
          "204":
            description: OK
            schema:
              $ref: '#/definitions/Cat'
          "404":
            description: Not found
        """
        cat = CATS.pop(1)
        return JSONResponse(cat)


# define doc by yaml or json file
@app.route("/cats/", methods=["GET"])
@openapi.from_file("./examples/docs/cats_get.yml")
def list_cats(req: Request):
    return JSONResponse(list(CATS.values()))


@app.route("/cats/", methods=["POST"])
@openapi.from_file("./examples/docs/cats_post.json")
async def list_cats(req: Request):
    cat = await req.json()
    CATS[cat["id"]] = cat
    return JSONResponse(cat)


def test_app():
    client = TestClient(app)
    spec = openapi.load_specification(app)
    validate_v2_spec(spec)
    assert client.get(openapi.config["specification_url"]).json() == spec
    assert client.get(openapi.config["swagger_url"]).status_code == 200
    assert client.get(openapi.config["redoc_url"]).status_code == 200


if __name__ == "__main__":
    run(app)
```

Then we can get swagger web page at [http://localhost:8000/apiman/swagger/](http://localhost:8000/apiman/swagger/):
![WebPage](docs/SwaggerUI.jpg)

See **examples/** for more examples

## How it works

* Provide a base class("OpenApi") to handle api specification's collection
* Provide extentions to extract api specification and register http endpoints to show UI web page and specification
