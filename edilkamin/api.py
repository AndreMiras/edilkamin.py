import typing
from enum import Enum

import requests
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


def discover_devices_helper(
    devices: typing.Tuple[typing.Dict], convert=True
) -> typing.Tuple[str]:
    """
    Given a list of bluetooth addresses/names return the ones matching for Edilkamin.
    >>> devices = (
    ...     {"name": "EDILKAMIN_EP", "address": "01:23:45:67:89:AB"},
    ...     {"name": "another_device", "address": "AA:BB:CC:DD:EE:FF"},
    ... )
    >>> discover_devices_helper(devices)
    ('01:23:45:67:89:a9',)
    """
    matching_devices = filter(lambda device: device["name"] == "EDILKAMIN_EP", devices)
    matching_devices = map(
        lambda device: bluetooth_mac_to_wifi_mac(device["address"])
        if convert
        else device["address"],
        matching_devices,
    )
    return tuple(matching_devices)


def discover_devices(convert=True) -> typing.Tuple[str]:
    """
    Discover devices using bluetooth.
    Return the MAC addresses of the discovered devices.
    Return the addresses converted to device wifi/identifier instead of the BLE ones.
    """
    import simplepyble

    devices = ()
    adapters = simplepyble.Adapter.get_adapters()
    for adapter in adapters:
        adapter.scan_for(2000)
        devices += tuple(
            map(
                lambda device: {
                    "name": device.identifier(),
                    "address": device.address(),
                },
                adapter.scan_get_results(),
            )
        )
    return discover_devices_helper(devices, convert)


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


def check_connection(token: str, mac_address: str) -> str:
    """
    Check if the token is still valid.
    Return a "Command 00030529000154df executed successfully" on success.
    Raise an `HTTPError` exception otherwise.
    """
    return mqtt_command(token, mac_address, {"name": "check"})


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


def device_info_get_alarm_reset(info: typing.Dict) -> bool:
    """Get alarm reset value from cached info."""
    return info["status"]["commands"]["alarm_reset"]


def get_alarm_reset(token: str, mac_address: str) -> bool:
    """Get alarm reset value."""
    info = device_info(token, mac_address)
    return device_info_get_alarm_reset(info)


def device_info_get_perform_cochlea_loading(info: typing.Dict) -> bool:
    """Get perform cochlea loading state from cached info."""
    return info["status"]["commands"]["perform_cochlea_loading"]


def get_perform_cochlea_loading(token: str, mac_address: str) -> bool:
    """Get perform cochlea loading state."""
    info = device_info(token, mac_address)
    return device_info_get_perform_cochlea_loading(info)


def set_perform_cochlea_loading(token: str, mac_address: str, value: bool) -> str:
    """Set the perform cochlea loading value."""
    return mqtt_command(
        token, mac_address, {"name": "cochlea_loading", "value": bool(value)}
    )


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


def device_info_get_fan_1_speed(info: typing.Dict) -> int:
    """Get fans speed value from cached info."""
    return info["status"]["fans"]["fan_1_speed"]


def get_fan_1_speed(token: str, mac_address: str) -> int:
    """Get fans speed value."""
    info = device_info(token, mac_address)
    return device_info_get_fan_1_speed(info)


def set_fan_1_speed(token: str, mac_address: str, fan_1_speed: int) -> str:
    """
    Set fan 1 speed.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return mqtt_command(token, mac_address, {"name": "fan_1_speed", "value": fan_1_speed})


def device_info_get_fan_2_speed(info: typing.Dict) -> int:
    """Get fans speed value from cached info."""
    return info["status"]["fans"]["fan_2_speed"]


def get_fan_2_speed(token: str, mac_address: str) -> int:
    """Get fans speed value."""
    info = device_info(token, mac_address)
    return device_info_get_fan_2_speed(info)


def set_fan_2_speed(token: str, mac_address: str, fan_2_speed: int) -> str:
    info = device_info(token, mac_address)
    fan_number_confiuguration = info["nvm"]["installer_parameters"]["fans_number"]
    
    if fan_number_confiuguration >= 2:
        """
        Set fan 2 speed.
        Return response string e.g. "Command 0123456789abcdef executed successfully".
        """
        return mqtt_command(token, mac_address, {"name": "fan_2_speed", "value": fan_2_speed})


def device_info_get_fan_3_speed(info: typing.Dict) -> int:
    """Get fans speed value from cached info."""
    return info["status"]["fans"]["fan_3_speed"]


def get_fan_3_speed(token: str, mac_address: str) -> int:
    """Get fans speed value."""
    info = device_info(token, mac_address)
    return device_info_get_fan_3_speed(info)


def set_fan_3_speed(token: str, mac_address: str, fan_3_speed: int) -> str:
    info = device_info(token, mac_address)
    fan_number_confiuguration = info["nvm"]["installer_parameters"]["fans_number"]
    
    if fan_number_confiuguration >= 3:
        """
        Set fan 3 speed.
        Return response string e.g. "Command 0123456789abcdef executed successfully".
        """
        return mqtt_command(token, mac_address, {"name": "fan_3_speed", "value": fan_3_speed})


def device_info_get_airkare(info: typing.Dict) -> int:
    """Get airkare status from cached info."""
    return info["status"]["commands"]["airkare_function"]


def get_airkare(token: str, mac_address: str) -> int:
    """Get airkare status."""
    info = device_info(token, mac_address)
    return device_info_get_airkare(info)


def set_airkare(token: str, mac_address: str, airkare: bool) -> str:
    """
    Set airkare.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return mqtt_command(token, mac_address, {"name": "airkare_function", "value": airkare})


def device_info_get_relax_mode(info: typing.Dict) -> int:
    """Get relax mode status from cached info."""
    return info["nvm"]["user_parameters"]["is_relax_active"]


def get_relax_mode(token: str, mac_address: str) -> int:
    """Get relax mode status."""
    info = device_info(token, mac_address)
    return device_info_get_relax_mode(info)


def set_relax_mode(token: str, mac_address: str, relax_mode: bool) -> str:
    """
    Set relax mode.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return mqtt_command(token, mac_address, {"name": "relax_mode", "value": relax_mode})


def device_info_get_manual_power_level(info: typing.Dict) -> int:
    """Get manual power level value from cached info."""
    return info["nvm"]["user_parameters"]["manual_power"]


def get_manual_power_level(token: str, mac_address: str) -> int:
    """Get manual power level value."""
    info = device_info(token, mac_address)
    return device_info_get_relax_mode(info)


def set_manual_power_level(token: str, mac_address: str, manual_power_level: int) -> str:
    """
    Set manual power level value.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return mqtt_command(token, mac_address, {"name": "power_level", "value": manual_power_level}) 


def device_info_get_standby_mode(info: typing.Dict) -> int:
    """Get standby mode status from cached info."""
    return info["nvm"]["user_parameters"]["is_standby_active"]


def get_standby_mode(token: str, mac_address: str) -> int:
    """Get standby mode status."""
    info = device_info(token, mac_address)
    return device_info_get_standby_mode(info)


def set_standby_mode(token: str, mac_address: str, standby_mode: bool) -> str:
    info = device_info(token, mac_address)
    is_auto = info["nvm"]["user_parameters"]["is_auto"]
    
    if is_auto == True:
        """
        Set standby mode.
        Return response string e.g. "Command 0123456789abcdef executed successfully".
        """
        return mqtt_command(token, mac_address, {"name": "standby_mode", "value": standby_mode})
