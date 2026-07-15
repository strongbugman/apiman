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

Parameters such as `charset=utf-8` are ignored during matching. JSON and XML structured suffixes are treated semantically: for example, `application/problem+json` matches an `application/json` schema.

If the operation defines body schemas but the request content type matches none of them, validation fails with a missing-body-content error. A required `requestBody` or OpenAPI 2 `body` parameter rejects a missing `None` body even when the body schema itself would otherwise allow any value.

## Header names

HTTP header parameter names are case-insensitive. A specification that requires `X-Token` accepts `x-token`, `X-Token`, or `X-TOKEN` from the framework request object.

Query, cookie, and path parameter names remain case-sensitive because OpenAPI treats them as ordinary parameter names.

## Ignoring selected locations

Adapters may skip selected locations when framework behavior requires it:

```python
apiman.validate_request(request, ignore=["header"])
```

Use this narrowly: ignored data is not schema-validated.

## Repeated values and transport strings

Most frameworks expose query, header, and cookie values as strings. Their schemas should therefore use `type: string`. To represent numeric text, constrain the string with a pattern:

```yaml
schema:
  type: string
  pattern: '^\\d+$'
```

Repeated query and form values are preserved as lists when the framework exposes them. APIMAN accepts a single value or repeated values for array schemas:

```yaml
schema:
  type: array
  items:
    type: string
```

Repeated values for scalar schemas remain invalid. APIMAN does not parse comma-separated, space-separated, pipe-separated, or deep-object query serialization into nested structures; use repeated values for common arrays or parse those encodings before validation.

Use a JSON body when native integer, boolean, object, or nested array values are required.
