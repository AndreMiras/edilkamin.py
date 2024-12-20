import os
import sys

from setuptools import setup

REQUIRED_PYTHON = (3, 9)


def assert_python_version(version_info):
    current_python = version_info[:2]
    error_message = "Python {}.{} is required, but you're running Python {}.{}"
    error_message = error_message.format(*(REQUIRED_PYTHON + current_python))
    assert current_python >= REQUIRED_PYTHON, error_message


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        return f.read()


# exposing the params so it can be imported
setup_params = {
    "name": "edilkamin",
    "version": "1.4.1",
    "description": "Edilkamin Stove Python client",
    "long_description": read("README.md"),
    "long_description_content_type": "text/markdown",
    "author": "Andre Miras",
    "url": "https://github.com/AndreMiras/edilkamin.py",
    "packages": ["edilkamin"],
    "install_requires": [
        "pycognito",
        "requests",
    ],
    "extras_require": {
        "ble": ["simplepyble"],
        "dev": [
            "black",
            "coveralls",
            "flake8",
            "isort",
            "pytest",
            "pytest-cov",
            "tox",
            "twine",
            "wheel",
        ],
        "doc": [
            # fixes readthedocs build, refs:
            # https://github.com/readthedocs/readthedocs.org/issues/9038
            "Jinja2<3.1",
            "m2r2",
            "Sphinx",
            "sphinx-rtd-theme",
        ],
    },
}


def run_setup():
    assert_python_version(sys.version_info)
    setup(**setup_params)


# makes sure the setup doesn't run at import time
if __name__ == "__main__":
    run_setup()
