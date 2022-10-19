import os

from edilkamin import constants


def get_endpoint(url: str) -> str:
    return constants.BACKEND_URL + url


def get_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def assert_env(name: str) -> str:
    env = os.environ.get(name)
    assert env
    return env
