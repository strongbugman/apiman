# APIMAN

[![Build](https://github.com/strongbugman/apiman/workflows/test/badge.svg)](https://github.com/strongbugman/apiman/actions)
[![codecov](https://codecov.io/gh/strongbugman/apiman/branch/master/graph/badge.svg)](https://codecov.io/gh/strongbugman/apiman)

APIMAN provide a easy way to integrate api manual/document for your web project

## Features

* Out of the box for flask and Starlette
* Whole OpenAPI 2 and 3 specification support
* Provide configurable [SwaggerUI](http://swagger.io/swagger-ui/) and [RedocUI](https://rebilly.github.io/ReDoc/)
* Validate request(json body、query、header...) by API specification

## Install

```shell
pip install -U apiman
```

## Usage

### create openapi basic file

```yml
openapi: "3.0.0"
info:
  title: 'APIMAN'
  version: '0.1'
  description: 'API manual for example'
```

### create apiman instance

```python
from starlette.applications import Starlette
from apiman.starlette import Extension 
# from flask import Flask
# from apiman.flask import Extension

apiman = Extension(template="./docs/openapi.yml")
```

### register apiman

```python
# app = Flask(__name__)
app = Starlette()
openapi.init_app(app)
```

### add document for api endpoint

by docstring:

```python
@app.route("/hello/", methods=["GET"])
async def hello(req: Request):
    """
    There is normal docstring, Below is OpenAPI specification
    ---
    summary: hello api
    tags:
    - test
    parameters:
    - name: name
      in: query
      required: True
      schema:
        type: string
    responses:
      "200":
        description: OK
    """
    return Response(f"hello")
```

by yaml content:

```python
@app.route("/hello/", methods=["GET"])
@openapi.from_yaml(
    """
    summary: hello api
    tags:
    - test
    parameters:
    - name: name
      in: query
      required: True
      schema:
        type: string
    responses:
      "200":
        description: OK
    """
)
async def hello(req: Request):
    return Response(f"hello")
```

(why yaml content? for my usage, just for f-string support)

by file:

```python
@app.route("/hello/", methods=["GET"])
@openapi.from_file("./docs/hello.yml")
async def hello(req: Request):
    return Response(f"hello")

@app.route("/hello/", methods=["GET"])
@openapi.from_file("./docs/hello.json")
async def hello(req: Request):
    return Response(f"hello")
```


### run app and browse swagger ui at `server:port/apiman/swagger` or `server:port/apiman/redoc`

## More Usage

### Config apiman

Config apiman's ui url, title and ui html template

```python
apiman = Extension(
  title="OpenAPI document",
  specification_url="/apiman/specification/",
  swagger_url="/apiman/swagger/",
  redoc_url="/apiman/redoc/",
  swagger_template="swagger.html",
  redoc_template="redoc.html",
  template="template.yaml",
)
```
### reuseable schema

We can define some OpenAPI schema or parameters for config usage, in openapi.yml:

```yml
openapi: "3.0.0"
info:
  title: 'APIMAN'
  version: '0.1'
  description: 'API manual for example'
definitions:
  Cat:
    type: object
    required:
    - name
    properties:
      name:
        type: string
      age:
        type: integer
        format: int32
        minimum: 0
```

or by code:

```python
openapi.add_schema(
    "Cat",
    {
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0},
        },
        "type": "object",
    },
)
```

(All specification data store in `apiman.specification`), then use it by OpenAPI way:

```python
@openapi.from_yaml(
    """
    responses:
      "200":
        description: OK
        schema:
          $ref: '#definitions/Cat'
    """
)
```

### request validation

valide request by `validate_request`

```python
@app.route("/hello/", methods=["POST"])
@openapi.from_yaml(
    """
    summary: hello api
    tags:
    - test
    parameters:
    - name: name
      in: query
      required: True
      schema:
        type: string
    - name: x-custom-param
      schema:
        type: string
      in: header
      required: True
    - name: cookie_param
      schema:
        type: string
      in: cookie
    requesteBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              key:
                type: integer
            required: ["key"]
    responses:
      "200":
        description: OK
    """
)
async def get(self, req: Request):
    await req.json()
    openapi.validate_request(req)
    # get validated params
    request.query_params
    request.cookies
    request.headers
    request.json()
    ...
```

(for starlette, call `await req.json()` first to load json data)

This method will find this request's OpenAPI specification and request params(query, path, cookie, header, json body) then validate it, we can get validate req params by origin way or raise Exceptoin(by [jsonschema_rs](https://github.com/Stranger6667/jsonschema-rs/tree/master/bindings/python))


### limit

#### type limit

All request params type is **origin type**, so query/header/cookie params is always **string**, we should define this params type to string or we will get Exception(flask's path params can be int original).

But if we want some integer param for string type you can set regex `pattern` in specification, eg:

```yml
id:
  type: string
  pattern: '^\d+$'
```

or just use json body for rich format

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
      - name: x-client-version
        type: string
        in: header
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
        # validate params in path query header and cookie by schema (only support string type)
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
@app.route("/cats/", methods=["GET"])
@openapi.from_file("./examples/docs/cats_get.yml")
def list_cats(req: Request):
    return JSONResponse(list(CATS.values()))


@app.route("/cats/", methods=["POST"])
@openapi.from_file("./examples/docs/cats_post.json")
async def list_cats(req: Request):
    await req.json()
    # validate json body
    openapi.validate_request(req)
    cat = await req.json()
    CATS[cat["id"]] = cat
    return JSONResponse(cat)


if __name__ == "__main__":
    run(app)
```

Then we get swagger web page at [http://localhost:8000/apiman/swagger/](http://localhost:8000/apiman/swagger/):
![WebPage](docs/SwaggerUI.jpg)

See **examples/** for more examples

## How it works

* Provide a base class("OpenApi") to handle api specification's collection
* Provide extensions to extract api specification and register http endpoints to show UI web page and specification 