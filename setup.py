#!/usr/bin/env python3
from setuptools import setup, find_packages
import re

with open("starchart/__init__.py", "rt", encoding="utf8") as f:
    version = re.search(r"__version__ = \"(.*?)\"", f.read()).group(1)

requires = ["starlette>=0.11.1", "PyYAML>=3.13", "Jinja2>=2.10"]
tests_requires = [
    "pytest>=3.3.1",
    "pytest-cov>=2.5.1",
    "openapi_spec_validator>=0.2.4",
    "jsonschema<3",
    "uvicorn>=0.3.24",
]
setup_requires = ["pytest-runner>=3.0", "black"]

setup(
    name="starchart",
    version=version,
    url="https://github.com/strongbugman/starchart",
    description="Starlette's api document support",
    long_description=open("README.md").read(),
    author="Bruce Wu",
    author_email="strongbugman@gmail.com",
    license="BSD",
    classifiers=[
        "Environment :: Console",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=find_packages(exclude=("tests", "tests.*", "examples")),
    install_requires=requires,
    setup_requires=setup_requires,
    tests_require=tests_requires,
    include_package_data=True,
)
