import os
import unittest

from examples import _bottle, _falcon, _flask, _starlette, _tornado


def test_starltte():
    _starlette.test_app()


def test_flask():
    _flask.test_app()


def test_django():
    os.chdir(os.path.join("examples", "_django"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examples._django.fish.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(["", "test"])
    os.chdir(os.path.join("..", ".."))


def test_bottle():
    _bottle.test_app()


def test_tornado():
    result = unittest.TextTestRunner().run(
        unittest.TestLoader().loadTestsFromTestCase(_tornado.TestCase)
    )
    assert not result.errors
    assert not result.failures


def test_falcon():
    _falcon.test_app()
