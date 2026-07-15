# Writing Specifications

APIMAN can collect endpoint specifications from five sources.

## Docstrings

Place YAML after ordinary prose. If a separator is used, APIMAN parses the content after the final `---` marker.

```python
def hello(request):
    """
    Human-readable description.
    ---
    summary: Say hello
    responses:
      "200":
        description: OK
    """
```

Class-based handlers may define a method map at class level:

```yaml
get:
  summary: Read an item
  responses:
    "200":
      description: OK
delete:
  summary: Delete an item
  responses:
    "204":
      description: Deleted
```

## YAML strings

```python
@apiman.from_yaml(
    """
    summary: Create an item
    responses:
      "201":
        description: Created
    """
)
def create_item(request):
    ...
```

## Dictionaries

```python
@apiman.from_dict(
    {
        "summary": "Read an item",
        "responses": {"200": {"description": "OK"}},
    }
)
def read_item(request):
    ...
```

## YAML and JSON files

```python
@apiman.from_file("docs/items_get.yml")
def list_items(request):
    ...
```

## Reusable schemas

Add a schema programmatically:

```python
apiman.add_schema(
    "Item",
    {
        "type": "object",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
        },
        "required": ["id", "name"],
    },
)
```

APIMAN stores OpenAPI 3 schemas under `components.schemas` and OpenAPI 2 schemas under `definitions`.

## Validate or export the assembled document

```python
apiman.validate_specification()
apiman.generate_specification_file("openapi.yml")
apiman.generate_specification_file("openapi.json")
```

`validate_specification` selects the bundled OpenAPI schema based on the root `openapi` or `swagger` version. APIMAN supports Swagger/OpenAPI 2.0, OpenAPI 3.0.x, and OpenAPI 3.1.x documents.

## Refresh collected routes

APIMAN caches collected route metadata and compiled path schemas. Programmatic changes made through `add_schema` or `add_path` invalidate those caches automatically.

Use `reset()` when you need to clear cached route and validation state without collecting routes immediately:

```python
apiman.reset()
```

Use `reload(...)` after changing framework routes at runtime. It clears caches, then calls the adapter's `load_specification` method with the arguments you pass:

```python
apiman.reload(app)
```
