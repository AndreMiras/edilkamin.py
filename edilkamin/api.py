import typing

import requests
from pycognito import Cognito

from edilkamin import constants
from edilkamin.utils import get_endpoint, get_headers


def sign_in(username: str, password: str) -> str:
    """Sign in and return token."""
    cognito = Cognito(constants.USER_POOL_ID, constants.CLIENT_ID, username=username)
    cognito.authenticate(password)
    user = cognito.get_user()
    return user._metadata["access_token"]


def device_info(token: str, mac: str) -> typing.Dict:
    """Retrieve device info for a given MAC address in the format `aabbccddeeff`."""
    headers = get_headers(token)
    url = get_endpoint(f"device/{mac}/info")
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def mqtt_command(token: str, mac_address: str, payload: typing.Dict) -> str:
    """
    Send a MQTT command to the device identified with the MAC address.
    Return the response string.
    """
    headers = get_headers(token)
    url = get_endpoint("mqtt/command")
    data = {"mac_address": mac_address, **payload}
    response = requests.put(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()


def set_power(token: str, mac_address: str, value: int) -> str:
    """
    Set device power on (1) or off (0).
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return mqtt_command(token, mac_address, {"name": "power", "value": value})


def set_power_on(token: str, mac_address: str) -> str:
    return set_power(token, mac_address, 1)


def set_power_off(token: str, mac_address: str) -> str:
    return set_power(token, mac_address, 0)
