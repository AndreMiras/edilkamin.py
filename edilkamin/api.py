import typing
import warnings
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
        lambda device: (
            bluetooth_mac_to_wifi_mac(device["address"])
            if convert
            else device["address"]
        ),
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


def valid_fan_id_or_warning(info: typing.Dict, fan_id):
    fans_number = info["nvm"]["installer_parameters"]["fans_number"]
    if fans_number < fan_id:
        warnings.warn(f"Only {fans_number} fan(s) available.")
    return fans_number >= fan_id


def device_info_get_fan_speed(info: typing.Dict, fan_id: int) -> int:
    """Get fan id speed value from cached info."""
    return info["status"]["fans"][f"fan_{fan_id}_speed"]


def get_fan_speed(token: str, mac_address: str, fan_id: int) -> int:
    """Get fan id speed value."""
    info = device_info(token, mac_address)
    if not valid_fan_id_or_warning(info, fan_id):
        return 0
    return device_info_get_fan_speed(info, fan_id)


def set_fan_speed(token: str, mac_address: str, fan_id: int, speed: int) -> str:
    """
    Set fan id speed.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    info = device_info(token, mac_address)
    if not valid_fan_id_or_warning(info, fan_id):
        return ""
    return mqtt_command(
        token, mac_address, {"name": f"fan_{fan_id}_speed", "value": speed}
    )


def device_info_get_airkare(info: typing.Dict) -> bool:
    """Get airkare status from cached info."""
    return info["status"]["flags"]["is_airkare_active"]


def get_airkare(token: str, mac_address: str) -> bool:
    """Get airkare status."""
    info = device_info(token, mac_address)
    return device_info_get_airkare(info)


def set_airkare(token: str, mac_address: str, airkare: bool) -> str:
    """
    Set airkare.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return mqtt_command(
        token, mac_address, {"name": "airkare_function", "value": airkare}
    )


def device_info_get_relax_mode(info: typing.Dict) -> bool:
    """Get relax mode status from cached info."""
    return info["status"]["flags"]["is_relax_active"]


def get_relax_mode(token: str, mac_address: str) -> bool:
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
    return device_info_get_manual_power_level(info)


def set_manual_power_level(
    token: str, mac_address: str, manual_power_level: int
) -> str:
    """
    Set manual power level value.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return mqtt_command(
        token, mac_address, {"name": "power_level", "value": manual_power_level}
    )


def device_info_get_standby_mode(info: typing.Dict) -> bool:
    """Get standby mode status from cached info."""
    return info["nvm"]["user_parameters"]["is_standby_active"]


def get_standby_mode(token: str, mac_address: str) -> bool:
    """Get standby mode status."""
    info = device_info(token, mac_address)
    return device_info_get_standby_mode(info)


def set_standby_mode(token: str, mac_address: str, standby_mode: bool) -> str:
    """
    Set standby mode.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    info = device_info(token, mac_address)
    is_auto = info["nvm"]["user_parameters"]["is_auto"]
    if not is_auto:
        warnings.warn("Standby mode is only available from auto mode.")
        return ""
    return mqtt_command(
        token, mac_address, {"name": "standby_mode", "value": standby_mode}
    )


def device_info_get_chrono_mode(info: typing.Dict) -> bool:
    """Get chrono mode status from cached info."""
    return info["status"]["flags"]["is_crono_active"]


def get_chrono_mode(token: str, mac_address: str) -> bool:
    """Get chrono mode status."""
    info = device_info(token, mac_address)
    return device_info_get_chrono_mode(info)


def set_chrono_mode(token: str, mac_address: str, chrono_mode: bool) -> str:
    """
    Set chrono mode.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return mqtt_command(
        token, mac_address, {"name": "chrono_mode", "value": chrono_mode}
    )


def device_info_get_easy_timer(info: typing.Dict) -> int:
    """Get easy timer value from cached info."""
    easy_time_status = info["status"]["flags"]["is_easytimer_active"]
    return info["status"]["easytimer"]["time"] if easy_time_status else 0


def get_easy_timer(token: str, mac_address: str) -> int:
    """Get easy timer value, return 0 if disabled."""
    info = device_info(token, mac_address)
    return device_info_get_easy_timer(info)


def set_easy_timer(token: str, mac_address: str, easy_timer: int) -> str:
    """
    Set easy timer value.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return mqtt_command(token, mac_address, {"name": "easytimer", "value": easy_timer})


def device_info_get_autonomy_time(info: typing.Dict) -> int:
    """Get autonomy time from cached info."""
    return info["status"]["pellet"]["autonomy_time"]


def get_autonomy_time(token: str, mac_address: str) -> int:
    """Get autonomy time."""
    info = device_info(token, mac_address)
    return device_info_get_autonomy_time(info)


def device_info_get_pellet_reserve(info: typing.Dict) -> bool:
    """Get pellet reserve status from cached info."""
    return info["status"]["flags"]["is_pellet_in_reserve"]


def get_pellet_reserve(token: str, mac_address: str) -> bool:
    """Get pellet reserve status."""
    info = device_info(token, mac_address)
    return device_info_get_pellet_reserve(info)
