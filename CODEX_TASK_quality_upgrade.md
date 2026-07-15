# Codex Task: APIMAN correctness, compatibility, tests, and release-quality upgrade

## Goal

Improve APIMAN's runtime correctness, OpenAPI behavior, framework compatibility, security/reproducibility, tests, and release idempotency based on the completed review. Produce a focused, backward-compatible patch with real verification. Do not commit or push.

## Repository and current state

- Repository: `/root/code/github/apiman`
- Branch: `master`
- Existing public API centers on `Apiman`, `init_app`, `from_yaml`, `from_dict`, `from_file`, `validate_request`, `async_validate_request`, `validate_specification`, `add_schema`, and `add_path`.
- The recently modernized engineering baseline is already in HEAD: PEP 621, uv, Ruff, Mypy, Nox, MkDocs, GitHub Actions.
- There is one intentional uncommitted change in `.github/workflows/test-and-release.yml`: release depends on `[test, docs]`, not `deploy-docs`, so Pages failures do not block package releases. Preserve it.
- Do not commit, push, publish, tag, or access secrets.
- Do not rewrite the package into a different architecture or migrate to `src/` layout in this task.
- Read `/root/wiki/concepts/python-project-standards.md` before editing.

## Mandatory issues to address

### 1. Correct OpenAPI 2.0 / 3.0 / 3.1 specification validation

Current `base.py::validate_specification` routes every OpenAPI major version 3 document to `openapi3.1_schema.yaml`, so valid 3.0.x documents fail.

Implement trustworthy version-specific validation. Do not invent a hand-written incomplete OpenAPI schema. Use an authoritative maintained validator or authoritative bundled schemas. Preserve OpenAPI 2 support. Add tests proving valid 2.0, 3.0.x, and 3.1.x documents pass and invalid documents fail.

### 2. HTTP header names must be case-insensitive

Normalize OpenAPI header parameter names and adapter-extracted request headers consistently. Add tests proving an OpenAPI `X-Token` requirement accepts `x-token`, `X-TOKEN`, etc. Preserve non-header parameter case semantics.

### 3. Cache and specification reload correctness

`_path_schemas` can become stale after `add_path` / `add_schema`, and one-shot `loaded` route discovery ignores later changes. Add intentional cache invalidation and a public, documented reload/reset API that framework adapters can use safely. Do not introduce global monkey patches. Add focused tests.

### 4. Improve request-validation semantics

At minimum:
- Preserve full OpenAPI 2 parameter constraints, not only `type` (e.g. pattern, enum, min/max, arrays/items where supported).
- Enforce `requestBody.required` even when the body schema itself permits an empty value.
- Handle media type matching robustly (charset parameters and structured JSON media types such as `application/problem+json` when semantically appropriate).
- Keep behavior explicit for repeated/multi-value query parameters; support common array cases if feasible and document remaining limits.
- Maintain sync/async validation APIs.

Add unit tests for each behavior. Do not merely lower assertions or skip tests.

### 5. Fix clear adapter defects and reduce private-API fragility

- Fix repeated `if self.redoc_template and self.redoc_template` checks to use `redoc_url`.
- Prefer documented public APIs over private attributes in Starlette, Django, Falcon, and Tornado.
- Where a framework genuinely exposes no stable public introspection API, isolate the compatibility access behind a small helper, guard it defensively, and test it. Do not monkey-patch frameworks or vendor fake framework facades.
- Preserve all six framework integrations and both Falcon WSGI/ASGI behavior.
- Avoid module-import-time failures in the Django adapter where practical without breaking existing usage.

### 6. Pin or bundle Swagger UI / ReDoc browser assets

Remove `@latest` CDN references. Use explicit stable versions. Prefer reproducible assets; if keeping CDN references, document the network/CSP implication and use integrity metadata only if verified against the exact files. Do not fabricate SRI hashes.

### 7. Make release workflow recoverable and idempotent

Current workflow treats an existing git tag as proof that PyPI publication and GitHub Release creation both succeeded. Fix this state model.

Desired behavior for version V:
- Independently detect whether PyPI version V exists, whether git tag V exists, and whether GitHub Release V exists.
- Build/publish only when PyPI version is absent.
- Ensure the tag exists after a successful/previous PyPI publication.
- Ensure GitHub Release exists and contains artifacts.
- A failed publish followed by rerun must recover instead of permanently skipping.
- Preserve the repository's unprefixed tag convention (`0.5.4`, not `v0.5.4`).
- Keep package release independent of GitHub Pages deployment.
- Use OIDC, no static PyPI token.
- Add a testable local script for release-state decision logic if that makes the workflow safer; unit-test it without network.

### 8. Resolve Python support claim mismatch

CI tests 3.9-3.12 while metadata claims >=3.8. Choose and document one coherent policy. Prefer raising the next development baseline to >=3.9 unless preserving 3.8 is low-cost and actually tested. Do not bump the package version in this task.

### 9. Expand tests and tighten quality configuration

- Add focused unit tests for base behavior instead of relying only on six broad example tests.
- Keep all existing tests passing.
- Do not add per-file Ruff exclusions or `extend-exclude` entries.
- Reduce broad Ruff/Mypy ignores when the corrected code makes them unnecessary.
- Format maintained Python files uniformly with Ruff.
- Do not game coverage by omitting files or lowering the threshold.

## Documentation requirements

Update README/MkDocs for:
- exact OpenAPI versions supported;
- request-validation semantics and limits;
- header case behavior;
- reload/reset API;
- pinned/bundled UI asset network implications;
- coherent Python version support;
- release recovery behavior where maintainers need it.

Keep examples accurate and runnable.

## Acceptance criteria

Run and report exact results for all of the following:

```bash
make format
make test
make test-all
make docs
make build
```

Also verify:

```bash
git diff --check
```

Inspect the wheel to prove required `apiman/static/*` assets and any new schema/static files are packaged.

## Constraints

- No commit, push, tag, release, or publication.
- No secrets or auth-file reads.
- No fake local substitute for a real dependency.
- No broad test skips, coverage reductions, or per-file lint exclusions.
- Preserve unrelated user changes.
- Prefer small, reviewable helpers and tests over sweeping rewrites.
- If a desired change cannot be done safely while retaining compatibility, document the blocker and implement the strongest verified subset rather than guessing.

## Final response expected from Codex

Return:
1. concise summary of design decisions;
2. files changed;
3. exact verification commands and results;
4. remaining risks or deliberate compatibility limits.
