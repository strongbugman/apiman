import os
from importlib import import_module
from pkgutil import iter_modules

import examples


def test_examples():
    for _, name, _ in iter_modules(examples.__path__):
        example = import_module(f"examples.{name}")
        example.test_app()

    os.chdir(os.path.join("examples", "fish"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "examples.fish.fish.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(["", "test"])
