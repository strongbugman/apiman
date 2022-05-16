# APIMAN

[![Build](https://github.com/strongbugman/apiman/workflows/test/badge.svg)](https://github.com/strongbugman/apiman/actions)
[![codecov](https://codecov.io/gh/strongbugman/apiman/branch/master/graph/badge.svg)](https://codecov.io/gh/strongbugman/apiman)

APIMAN provide a easy way to integrate OPENAPI manual/document for python web project

## Features

* Out of the box for Starlette, Flask, Django, Bottle, Tornado and Falcon
* Whole OpenAPI 2 and 3 specification support
* Configurable [SwaggerUI](http://swagger.io/swagger-ui/) and [RedocUI](https://rebilly.github.io/ReDoc/)
* Request data(json/xml/form body, query, header, cookie, path args) validation by API specification

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
from apiman.starlette import Apiman 
# from flask import Flask
# from apiman.flask import Apiman

apiman = Apiman(template="./docs/openapi.yml")
```

### register apiman

```python
# app = Flask(__name__)
app = Starlette()
apiman.init_app(app)
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
@apiman.from_yaml(
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
@apiman.from_file("./docs/hello.yml")
async def hello(req: Request):
    return Response(f"hello")

@app.route("/hello/", methods=["GET"])
@apiman.from_file("./docs/hello.json")
async def hello(req: Request):
    return Response(f"hello")
```

### validate defined OPENAPI specification

```python
apiman.validate_specification()
```

### run app and browse swagger ui at `server:port/apiman/swagger` or `server:port/apiman/redoc`

## More Usage

### Config apiman

Config apiman's ui url, title and ui html template

```python
apiman = Apiman(
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
apiman.add_schema(
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
@apiman.from_yaml(
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
@apiman.from_yaml(
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
    # await req.json()
    # apiman.validate_request(req)
    await apiman.async_validate_request(req)
    # get validated params by original ways
    request.query_params
    request.cookies
    request.headers
    request.json()
    ...
```

(for sync code, call `apiman.validate_request(req)`)

This method will find this request's OpenAPI specification and request params(query, path, cookie, header, body) then validate it, we can assess validated req params by origin way or raise validation exception.(by [jsonschema_rs](https://github.com/Stranger6667/jsonschema-rs/tree/master/bindings/python))


### limit

#### type limit

All request params type is **origin type**, so query/header/cookie params is always **string**, we should define this params type to string or we will get validation Exception(eg, flask's path params can be int type original).

But if we want some integer param for string type, set regex `pattern` in specification, eg:

```yml
id:
  type: string
  pattern: '^\d+$'
```

or just use body data for rich format

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
from starlette.testclient import TestClient

from apiman.starlette import Apiman


app = Starlette()
apiman = Apiman(template="./examples/docs/cat_template.yml")
apiman.init_app(app)


# define data
CATS = {
    1: {"id": 1, "name": "DangDang", "age": 2},
    2: {"id": 2, "name": "DingDing", "age": 1},
}
# add schema definition
apiman.add_schema(
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
        apiman.validate_request(req)
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
@apiman.from_file("./examples/docs/cats_get.yml")
def list_cats(req: Request):
    return JSONResponse(list(CATS.values()))


@app.route("/cats/", methods=["POST"])
@apiman.from_file("./examples/docs/cats_post.json")
async def list_cats(req: Request):
    await req.json()
    # validate json body
    apiman.validate_request(req)
    cat = await req.json()
    CATS[cat["id"]] = cat
    return JSONResponse(cat)


if __name__ == "__main__":
    apiman.validate_specification()
    run(app)
```

Then we get swagger web page at [http://localhost:8000/apiman/swagger/](http://localhost:8000/apiman/swagger/):
![WebPage](docs/SwaggerUI.jpg)

See **examples/** for more examples

## How it works

* Provide a base class to handle api specification's collection
* Provide extension for every web framework to extract api specification and register http endpoints to show UI web page and specification 
