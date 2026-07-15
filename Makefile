all: test

version = $(shell python3 -c 'import re; print(re.search(r"version\s*=\s*\"([^\"]+)\"", open("pyproject.toml").read()).group(1))')

.PHONY: all install env-info lint format test test-all docs docs-serve build clean

install:
	uv sync --all-extras

env-info:
	@printf 'Project: %s\n' "$(CURDIR)"
	@printf 'uv:      %s\n' "$$(command -v uv || printf 'not found')"
	@printf 'Python:  %s\n' "$$(uv run python -c 'import sys; print(sys.executable)')"
	@uv run python --version

lint:
	uv run ruff check apiman tests
	uv run mypy apiman

test: install lint
	uv run pytest --cov apiman --cov-report term-missing tests/

test-all: install
	uv run --with nox --with nox-uv nox

# Formatting is intentionally explicit: it rewrites maintained Python files.
format:
	-uv run ruff check --fix apiman tests examples
	uv run ruff format apiman tests examples

docs: install
	uv run mkdocs build --strict

docs-serve: install
	uv run mkdocs serve

build: clean
	uv build

clean:
	rm -rf .eggs *.egg-info dist build site .nox .pytest_cache .coverage .ruff_cache .mypy_cache .venv
