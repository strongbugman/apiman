import os

from examples import _flask, _bottle, _starlette


def test_starltte():
    _starlette.test_app()


def test_flask():
    _flask.test_app()


def test_django():
    os.chdir(os.path.join("examples", "_django"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examples._django.fish.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(["", "test"])


def test_bottle():
    _bottle.test_app()
