# Framework Integrations

APIMAN provides one adapter module per supported framework. The common pattern is to import the adapter-specific `Apiman`, construct it, and register it with the application.

| Framework | Import | Registration | Example |
|---|---|---|---|
| Starlette | `from apiman.starlette import Apiman` | `apiman.init_app(app)` | `examples/_starlette.py` |
| Flask | `from apiman.flask import Apiman` | `apiman.init_app(app)` | `examples/_flask.py` |
| Bottle | `from apiman.bottle import Apiman` | `apiman.init_app(app)` | `examples/_bottle.py` |
| Tornado | `from apiman.tornado import Apiman` | `apiman.init_app(app)` | `examples/_tornado.py` |
| Falcon | `from apiman.falcon import Apiman` | `apiman.init_app(app)` | `examples/_falcon.py` |
| Django | `from apiman.django import apiman` | Configure through the Django adapter | `examples/_django/` |

## Synchronous and asynchronous requests

Use `validate_request` when the adapter can read request data synchronously:

```python
apiman.validate_request(request)
```

Use `async_validate_request` when request-body extraction must be awaited:

```python
await apiman.async_validate_request(request)
```

The Starlette and Falcon ASGI examples demonstrate asynchronous validation. The Flask, Bottle, Django, Tornado, and Falcon WSGI examples demonstrate synchronous validation.

## Application discovery

During registration, each adapter adds the documentation endpoints and discovers route handlers in the framework's native routing table. Keep route declarations and APIMAN decorators attached to the actual handler functions or classes; wrapper decorators that discard metadata can prevent discovery.

See the complete runnable applications under [`examples/`](https://github.com/strongbugman/apiman/tree/master/examples) for framework-specific routing details.
