# Development and Release

APIMAN follows the same modern maintenance workflow as Danio: PEP 621 metadata, uv environments, Ruff linting, Nox version matrices, MkDocs, and one GitHub Actions test/release pipeline.

## Prerequisites

Install [uv](https://docs.astral.sh/uv/), then run:

```bash
make install
make env-info
```

## Quality gates

```bash
make lint      # Ruff checks and mypy
make test      # install, lint, pytest, and coverage
make test-all  # isolated Python 3.9-3.12 Nox sessions
make docs      # strict MkDocs build
make build     # build wheel and source distribution
```

`make format` is intentionally separate because it rewrites Python files. Run it only when source formatting changes are in scope.

## Documentation preview

```bash
make docs-serve
```

Open the local URL printed by MkDocs. `make docs` uses strict mode, so broken internal links, missing nav pages, and documentation warnings fail CI.

## Dependency policy

- Runtime dependencies live in `[project].dependencies`.
- Test, framework, typing, lint, and docs tools live in `[project.optional-dependencies].test`.
- APIMAN is a library, so no `uv.lock` file is committed; downstream applications resolve versions appropriate to their own environment.

## CI/CD behavior

The `Test and Release` workflow runs on pushes and pull requests targeting `master`:

1. Test Python 3.9, 3.10, 3.11, and 3.12.
2. Upload test coverage to Codecov.
3. Build the documentation in strict mode; pushes to `master` publish it to GitHub Pages.
4. On a successful push to `master`, compare the `pyproject.toml` version with existing tags.
5. If the version tag is new, build distributions, publish through PyPI Trusted Publishing (OIDC), and create a GitHub Release.

APIMAN retains its existing unprefixed release-tag convention, such as `0.5.4`.

!!! warning "PyPI configuration"
    The GitHub repository must be registered as a Trusted Publisher for the `apiman` project on PyPI before OIDC publishing can succeed.

## Version and release process

The project version has one source of truth: `pyproject.toml`.

1. Update `[project].version` in `pyproject.toml`.
2. Run `make test`, `make docs`, and `make build`.
3. Commit and merge to `master`.
4. The workflow creates the matching tag and release only after every required job passes.
