# Getting Started

## Install

APIMAN supports Python 3.9 through 3.12.

Install APIMAN and your chosen framework:

```bash
pip install apiman starlette uvicorn
```

## Create an application

```python
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from apiman.starlette import Apiman

app = Starlette()
apiman = Apiman()
apiman.init_app(app)


@app.route("/hello", methods=["GET"])
async def hello(request: Request):
    """
    summary: Say hello
    parameters:
      - name: name
        in: query
        required: true
        schema:
          type: string
    responses:
      "200":
        description: Successful response
    """
    apiman.validate_request(request)
    return JSONResponse({"message": f"Hello, {request.query_params['name']}!"})
```

Run it:

```bash
uvicorn app:app --reload
```

Then browse to `/apiman/swagger/` or `/apiman/redoc/`.

## Use a custom base document

Pass a YAML or JSON template containing the root OpenAPI object:

```python
apiman = Apiman(template="docs/openapi.yml")
```

```yaml
openapi: "3.1.0"
info:
  title: Example API
  version: "1.0"
paths: {}
```

## Customize endpoints and title

```python
apiman = Apiman(
    title="Example API documentation",
    specification_url="/openapi.json",
    swagger_url="/docs/",
    redoc_url="/redoc/",
    template="docs/openapi.yml",
)
```

Call `init_app` after creating the framework application and before serving requests.
