import nox

nox.options.default_venv_backend = "uv"
nox.options.sessions = ["tests"]


@nox.session(python=["3.9", "3.10", "3.11", "3.12"])
def tests(session: nox.Session) -> None:
    """Run linting, type checking, and tests across supported Python versions."""
    session.install("-e", ".[test]")
    session.run("ruff", "check", "apiman", "tests")
    session.run("mypy", "apiman")
    session.run("pytest", "--cov=apiman", "tests/", *session.posargs)
