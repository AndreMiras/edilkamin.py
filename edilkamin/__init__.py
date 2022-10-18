#!/usr/bin/env python
import os
import typing

import requests
from pycognito import Cognito

from edilkamin import constants


def sign_in(username, password):
    cognito = Cognito(constants.USER_POOL_ID, constants.CLIENT_ID, username=username)
    cognito.authenticate(password)
    user = cognito.get_user()
    return user._metadata["access_token"]


def get_endpoint(url: str) -> str:
    return constants.BACKEND_URL + url


def get_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def device_info(token: str, mac: str):
    headers = get_headers(token)
    url = get_endpoint(f"device/{mac}/info")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def mqtt_command(
    token: str, mac_address: str, payload: typing.Dict
) -> requests.models.Response:
    headers = get_headers(token)
    url = get_endpoint("mqtt/command")
    data = {"mac_address": mac_address, **payload}
    response = requests.put(url, json=data, headers=headers)
    response.raise_for_status()
    return response


def set_power(token: str, mac_address: str, value: int) -> requests.models.Response:
    return mqtt_command(token, mac_address, {"name": "power", "value": value})


def set_power_on(token: str, mac_address: str):
    return set_power(token, mac_address, 1)


def set_power_off(token: str, mac_address: str):
    return set_power(token, mac_address, 0)


def assert_env(name: str) -> str:
    env = os.environ.get(name)
    assert env
    return env


def main():
    username = assert_env("USERNAME")
    password = assert_env("PASSWORD")
    mac_address = assert_env("MAC_ADDRESS")
    token = sign_in(username, password)
    info = device_info(token, mac_address)
    print(info)
    result = set_power_off(token, mac_address)
    print(result)


if __name__ == "__main__":
    main()
