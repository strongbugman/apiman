# APIMAN

[![Test and Release](https://github.com/strongbugman/apiman/actions/workflows/test-and-release.yml/badge.svg)](https://github.com/strongbugman/apiman/actions/workflows/test-and-release.yml)
[![PyPI version](https://badge.fury.io/py/apiman.svg)](https://pypi.org/project/apiman/)
[![Codecov coverage](https://codecov.io/gh/strongbugman/apiman/branch/master/graph/badge.svg)](https://codecov.io/gh/strongbugman/apiman)
[![Python support](https://img.shields.io/pypi/pyversions/apiman.svg)](https://pypi.org/project/apiman/)
[![License](https://img.shields.io/github/license/strongbugman/apiman)](LICENSE)

**APIMAN** integrates OpenAPI documentation and schema-based request validation into Python web applications without requiring a framework rewrite.

## Features

- Integrations for **Starlette, Flask, Django, Bottle, Tornado, and Falcon**
- OpenAPI 2.0, OpenAPI 3.0.x, and OpenAPI 3.1.x specification validation
- Built-in Swagger UI and ReDoc endpoints
- Specifications from docstrings, YAML strings, dictionaries, YAML files, or JSON files
- Validation for query, header, cookie, path, JSON, XML, and form request data
- Synchronous and asynchronous validation APIs

## Installation

```bash
pip install -U apiman
```

Install the web framework you use separately, for example:

```bash
pip install starlette uvicorn
```

## Quick start

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

Run the application and open:

- Swagger UI: `http://localhost:8000/apiman/swagger/`
- ReDoc: `http://localhost:8000/apiman/redoc/`
- OpenAPI document: `http://localhost:8000/apiman/specification/`

## Documentation

The full guide covers framework setup, specification sources, reusable schemas, request validation, and project maintenance:

**[APIMAN documentation](https://strongbugman.github.io/apiman/)**

The documentation can also be built locally:

```bash
make docs
```

## Development

APIMAN supports Python 3.9 through 3.12. This project uses [uv](https://docs.astral.sh/uv/) and Ruff:

```bash
make install   # create/sync .venv
make lint      # Ruff + mypy
make test      # lint + tests + coverage
make test-all  # Python 3.9-3.12 via Nox
make docs      # strict MkDocs build
make build     # sdist and wheel
```

`make format` rewrites Python files and is intentionally separate from the read-only quality checks.

## Compatibility Notes

APIMAN validates assembled specifications with bundled OpenAPI 2.0, 3.0.x, and 3.1.x schemas. Header parameter names are matched case-insensitively; query, cookie, and path parameter names remain case-sensitive.

Request validation supports JSON, XML, form, query, header, cookie, and path inputs. Repeated query and form values are accepted for array schemas. Repeated values for scalar schemas remain invalid.

Use `apiman.reset()` to clear collected route/schema caches and `apiman.reload(...)` to clear caches and collect routes again through the active framework adapter.

The built-in Swagger UI and ReDoc templates use pinned jsDelivr CDN versions, not `@latest`. Serving those endpoints requires browser access to jsDelivr unless you customize the templates to serve local assets.

## License

APIMAN is licensed under the [BSD 3-Clause License](LICENSE).
