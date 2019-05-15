from importlib import import_module
from pkgutil import iter_modules

import examples


def test_examples():
    for _, name, _ in iter_modules(examples.__path__):
        example = import_module(f"examples.{name}")
        example.test_app()
