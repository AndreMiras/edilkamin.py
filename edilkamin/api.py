import typing
from enum import Enum

import requests
import simplepyble
from pycognito import Cognito

from edilkamin import constants
from edilkamin.utils import get_endpoint, get_headers


class Power(Enum):
    OFF = 0
    ON = 1


def sign_in(username: str, password: str) -> str:
    """Sign in and return token."""
    cognito = Cognito(constants.USER_POOL_ID, constants.CLIENT_ID, username=username)
    cognito.authenticate(password)
    user = cognito.get_user()
    return user._metadata["access_token"]


def format_mac(mac: str):
    return mac.replace(":", "").lower()


def bluetooth_mac_to_wifi_mac(mac: str) -> str:
    """
    >>> bluetooth_mac_to_wifi_mac("A8:03:2A:FE:D5:0B")
    'a8:03:2a:fe:d5:09'
    """
    mac = format_mac(mac)
    mac_int = int(mac, 16)
    mac_wifi_int = mac_int - 2
    mac_wifi = "{:012x}".format(mac_wifi_int)
    return ":".join(mac_wifi[i : i + 2] for i in range(0, len(mac_wifi), 2))


def discover_devices(convert=True) -> typing.List[str]:
    """
    Discover devices using bluetooth.
    Return the MAC addresses of the discovered devices.
    Return the addresses converted to device wifi/identifier instead of the BLE ones.
    """
    devices = []
    adapters = simplepyble.Adapter.get_adapters()
    for adapter in adapters:
        adapter.scan_for(2000)
        for device in adapter.scan_get_results():
            if device.identifier() == "EDILKAMIN_EP":
                mac = (
                    bluetooth_mac_to_wifi_mac(device.address())
                    if convert
                    else device.address()
                )
                devices.append(mac)
    return devices


def device_info(token: str, mac: str) -> typing.Dict:
    """Retrieve device info for a given MAC address in the format `aabbccddeeff`."""
    headers = get_headers(token)
    mac = format_mac(mac)
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
    data = {"mac_address": format_mac(mac_address), **payload}
    response = requests.put(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()


def set_power(token: str, mac_address: str, power: Power) -> str:
    """
    Set device power.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return mqtt_command(token, mac_address, {"name": "power", "value": power.value})


def device_info_get_power(info: typing.Dict) -> Power:
    """Get device current power value from cached info."""
    return Power(info["status"]["commands"]["power"])


def get_power(token: str, mac_address: str) -> Power:
    """Get device current power value."""
    info = device_info(token, mac_address)
    return device_info_get_power(info)


def set_power_on(token: str, mac_address: str) -> str:
    return set_power(token, mac_address, Power.ON)


def set_power_off(token: str, mac_address: str) -> str:
    return set_power(token, mac_address, Power.OFF)


def device_info_get_environment_temperature(info: typing.Dict) -> int:
    """Get environment temperature value from cached info."""
    return info["status"]["temperatures"]["enviroment"]


def get_environment_temperature(token: str, mac_address: str) -> Power:
    """Get environment temperature coming from sensor."""
    info = device_info(token, mac_address)
    return device_info_get_environment_temperature(info)


def device_info_get_target_temperature(info: typing.Dict) -> int:
    """Get target temperature value from cached info."""
    return info["nvm"]["user_parameters"]["enviroment_1_temperature"]


def get_target_temperature(token: str, mac_address: str) -> Power:
    """Get target temperature value."""
    info = device_info(token, mac_address)
    return device_info_get_target_temperature(info)


def set_target_temperature(token: str, mac_address: str, temperature: int) -> str:
    """
    Set target temperature in degree.
    Return response string e.g. "Command 0006052500b558ab executed successfully".
    """
    return mqtt_command(
        token, mac_address, {"name": "enviroment_1_temperature", "value": temperature}
    )
