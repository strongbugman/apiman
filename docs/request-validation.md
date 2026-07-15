# Request Validation

APIMAN derives JSON Schema fragments from the matched operation and validates request data with `jsonschema-rs`.

## Supported input locations

| OpenAPI input | Request source |
|---|---|
| `query` | Query-string parameters |
| `header` | HTTP headers |
| `cookie` | Cookies |
| `path` | Framework route parameters |
| `requestBody` / `body` | JSON, XML, or form body |
| `formData` | OpenAPI 2 form fields |

## Validate a request

```python
apiman.validate_request(request)
```

For adapters with asynchronous body access:

```python
await apiman.async_validate_request(request)
```

An invalid or missing value raises a `jsonschema_rs.ValidationError`. Translate that exception into the response format required by your application.

## Content types

Body validation selects a schema from the request's `Content-Type` header:

- `application/json`
- `application/xml`
- `application/x-www-form-urlencoded`
- `multipart/form-data`

If the operation defines body schemas but the request content type matches none of them, validation fails with a missing-body-content error.

## Ignoring selected locations

Adapters may skip selected locations when framework behavior requires it:

```python
apiman.validate_request(request, ignore=["header"])
```

Use this narrowly: ignored data is not schema-validated.

## String-valued transport parameters

Most frameworks expose query, header, and cookie values as strings. Their schemas should therefore use `type: string`. To represent numeric text, constrain the string with a pattern:

```yaml
schema:
  type: string
  pattern: '^\\d+$'
```

Use a JSON body when native integer, boolean, array, or object values are required.
