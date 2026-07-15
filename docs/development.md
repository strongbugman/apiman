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
3. Build the documentation in strict mode; pushes to `master` publish it to GitHub Pages in a separate `deploy-docs` job.
4. On a successful push to `master`, inspect PyPI, the unprefixed git tag, and the GitHub Release independently for the `pyproject.toml` version.
5. Build and publish distributions only when the PyPI version is absent. Publication uses PyPI Trusted Publishing (OIDC), not a static token.
6. Ensure the unprefixed tag exists after a successful or previous PyPI publication.
7. Ensure a GitHub Release exists and has distribution artifacts.

APIMAN retains its existing unprefixed release-tag convention, such as `0.5.4`.

Package release depends on the test and documentation build jobs, but not on GitHub Pages deployment. A Pages deployment failure must not block PyPI publication or release recovery.

!!! warning "PyPI configuration"
    The GitHub repository must be registered as a Trusted Publisher for the `apiman` project on PyPI before OIDC publishing can succeed.

## Version and release process

The project version has one source of truth: `pyproject.toml`.

1. Update `[project].version` in `pyproject.toml`.
2. Run `make test`, `make docs`, and `make build`.
3. Commit and merge to `master`.
4. The workflow recovers missing release pieces on rerun: PyPI, tag, and GitHub Release state are checked separately instead of treating an existing tag as proof that publication succeeded.
