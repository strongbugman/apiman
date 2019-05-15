#!/usr/bin/env python3
from setuptools import setup, find_packages
import re

with open("apiman/__init__.py", "r", encoding="utf8") as f:
    version = re.search(r"__version__ = \"(.*?)\"", f.read()).group(1)

requires = ["PyYAML>=3.13", "Jinja2>=2.10"]
tests_requires = [
    "pytest>=3.3.1",
    "pytest-cov>=2.5.1",
    "openapi_spec_validator==0.2.5",
    "jsonschema<3",
    "uvicorn>=0.3.24",
    "starlette>=0.11.1",
    "flask>=1.0",
]
setup_requires = ["pytest-runner>=3.0"]

setup(
    name="apiman",
    version=version,
    url="https://github.com/strongbugman/apiman",
    description="Integrate api manual for your web project",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
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
