import typing
import warnings
from enum import Enum

import httpx
from pycognito import Cognito

from edilkamin import constants
from edilkamin.async_dispatch import syncable
from edilkamin.buffer_utils import process_response
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


@syncable
async def device_info(token: str, mac: str) -> typing.Dict:
    """Retrieve device info for a given MAC address in the format `aabbccddeeff`.

    Automatically decompresses any gzip-compressed Buffer fields in the response.
    """
    headers = get_headers(token)
    mac = format_mac(mac)
    url = get_endpoint(f"device/{mac}/info")
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        raw_data = response.json()
        # Process response to decompress any Buffer fields
        return process_response(raw_data)


@syncable
async def mqtt_command(token: str, mac_address: str, payload: typing.Dict) -> str:
    """
    Send a MQTT command to the device identified with the MAC address.
    Return the response string.
    """
    headers = get_headers(token)
    url = get_endpoint("mqtt/command")
    data = {"mac_address": format_mac(mac_address), **payload}
    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()


@syncable
async def check_connection(token: str, mac_address: str) -> str:
    """
    Check if the token is still valid.
    Return a "Command 00030529000154df executed successfully" on success.
    Raise an `HTTPError` exception otherwise.
    """
    return await mqtt_command(token, mac_address, {"name": "check"})


@syncable
async def set_power(token: str, mac_address: str, power: Power) -> str:
    """
    Set device power.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return await mqtt_command(
        token, mac_address, {"name": "power", "value": power.value}
    )


def device_info_get_power(info: typing.Dict) -> Power:
    """Get device current power value from cached info."""
    return Power(info["status"]["commands"]["power"])


@syncable
async def get_power(token: str, mac_address: str) -> Power:
    """Get device current power value."""
    info = await device_info(token, mac_address)
    return device_info_get_power(info)


@syncable
async def set_power_on(token: str, mac_address: str) -> str:
    return await set_power(token, mac_address, Power.ON)


@syncable
async def set_power_off(token: str, mac_address: str) -> str:
    return await set_power(token, mac_address, Power.OFF)


def device_info_get_alarm_reset(info: typing.Dict) -> bool:
    """Get alarm reset value from cached info."""
    return info["status"]["commands"]["alarm_reset"]


@syncable
async def get_alarm_reset(token: str, mac_address: str) -> bool:
    """Get alarm reset value."""
    info = await device_info(token, mac_address)
    return device_info_get_alarm_reset(info)


def device_info_get_perform_cochlea_loading(info: typing.Dict) -> bool:
    """Get perform cochlea loading state from cached info."""
    return info["status"]["commands"]["perform_cochlea_loading"]


@syncable
async def get_perform_cochlea_loading(token: str, mac_address: str) -> bool:
    """Get perform cochlea loading state."""
    info = await device_info(token, mac_address)
    return device_info_get_perform_cochlea_loading(info)


@syncable
async def set_perform_cochlea_loading(token: str, mac_address: str, value: bool) -> str:
    """Set the perform cochlea loading value."""
    return await mqtt_command(
        token, mac_address, {"name": "cochlea_loading", "value": bool(value)}
    )


def device_info_get_environment_temperature(info: typing.Dict) -> int:
    """Get environment temperature value from cached info."""
    return info["status"]["temperatures"]["enviroment"]


@syncable
async def get_environment_temperature(token: str, mac_address: str) -> Power:
    """Get environment temperature coming from sensor."""
    info = await device_info(token, mac_address)
    return device_info_get_environment_temperature(info)


def device_info_get_target_temperature(info: typing.Dict) -> int:
    """Get target temperature value from cached info."""
    return info["nvm"]["user_parameters"]["enviroment_1_temperature"]


@syncable
async def get_target_temperature(token: str, mac_address: str) -> Power:
    """Get target temperature value."""
    info = await device_info(token, mac_address)
    return device_info_get_target_temperature(info)


@syncable
async def set_target_temperature(token: str, mac_address: str, temperature: int) -> str:
    """
    Set target temperature in degree.
    Return response string e.g. "Command 0006052500b558ab executed successfully".
    """
    return await mqtt_command(
        token, mac_address, {"name": "enviroment_1_temperature", "value": temperature}
    )


def valid_fan_id_or_warning(info: typing.Dict, fan_id):
    fans_number = info["nvm"]["installer_parameters"]["fans_number"]
    if fans_number < fan_id:
        warnings.warn(f"Only {fans_number} fan(s) available.", stacklevel=2)
    return fans_number >= fan_id


def device_info_get_fan_speed(info: typing.Dict, fan_id: int) -> int:
    """Get fan id speed value from cached info."""
    return info["status"]["fans"][f"fan_{fan_id}_speed"]


@syncable
async def get_fan_speed(token: str, mac_address: str, fan_id: int) -> int:
    """Get fan id speed value."""
    info = await device_info(token, mac_address)
    if not valid_fan_id_or_warning(info, fan_id):
        return 0
    return device_info_get_fan_speed(info, fan_id)


@syncable
async def set_fan_speed(token: str, mac_address: str, fan_id: int, speed: int) -> str:
    """
    Set fan id speed.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    info = await device_info(token, mac_address)
    if not valid_fan_id_or_warning(info, fan_id):
        return ""
    return await mqtt_command(
        token, mac_address, {"name": f"fan_{fan_id}_speed", "value": speed}
    )


def device_info_get_airkare(info: typing.Dict) -> bool:
    """Get airkare status from cached info."""
    return info["status"]["flags"]["is_airkare_active"]


@syncable
async def get_airkare(token: str, mac_address: str) -> bool:
    """Get airkare status."""
    info = await device_info(token, mac_address)
    return device_info_get_airkare(info)


@syncable
async def set_airkare(token: str, mac_address: str, airkare: bool) -> str:
    """
    Set airkare.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return await mqtt_command(
        token, mac_address, {"name": "airkare_function", "value": airkare}
    )


def device_info_get_relax_mode(info: typing.Dict) -> bool:
    """Get relax mode status from cached info."""
    return info["status"]["flags"]["is_relax_active"]


@syncable
async def get_relax_mode(token: str, mac_address: str) -> bool:
    """Get relax mode status."""
    info = await device_info(token, mac_address)
    return device_info_get_relax_mode(info)


@syncable
async def set_relax_mode(token: str, mac_address: str, relax_mode: bool) -> str:
    """
    Set relax mode.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return await mqtt_command(
        token, mac_address, {"name": "relax_mode", "value": relax_mode}
    )


def device_info_get_manual_power_level(info: typing.Dict) -> int:
    """Get manual power level value from cached info."""
    return info["nvm"]["user_parameters"]["manual_power"]


@syncable
async def get_manual_power_level(token: str, mac_address: str) -> int:
    """Get manual power level value."""
    info = await device_info(token, mac_address)
    return device_info_get_manual_power_level(info)


@syncable
async def set_manual_power_level(
    token: str, mac_address: str, manual_power_level: int
) -> str:
    """
    Set manual power level value.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return await mqtt_command(
        token, mac_address, {"name": "power_level", "value": manual_power_level}
    )


def device_info_get_standby_mode(info: typing.Dict) -> bool:
    """Get standby mode status from cached info."""
    return info["nvm"]["user_parameters"]["is_standby_active"]


@syncable
async def get_standby_mode(token: str, mac_address: str) -> bool:
    """Get standby mode status."""
    info = await device_info(token, mac_address)
    return device_info_get_standby_mode(info)


@syncable
async def set_standby_mode(token: str, mac_address: str, standby_mode: bool) -> str:
    """
    Set standby mode.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    info = await device_info(token, mac_address)
    is_auto = info["nvm"]["user_parameters"]["is_auto"]
    if not is_auto:
        warnings.warn("Standby mode is only available from auto mode.", stacklevel=2)
        return ""
    return await mqtt_command(
        token, mac_address, {"name": "standby_mode", "value": standby_mode}
    )


def device_info_get_chrono_mode(info: typing.Dict) -> bool:
    """Get chrono mode status from cached info."""
    return info["status"]["flags"]["is_crono_active"]


@syncable
async def get_chrono_mode(token: str, mac_address: str) -> bool:
    """Get chrono mode status."""
    info = await device_info(token, mac_address)
    return device_info_get_chrono_mode(info)


@syncable
async def set_chrono_mode(token: str, mac_address: str, chrono_mode: bool) -> str:
    """
    Set chrono mode.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return await mqtt_command(
        token, mac_address, {"name": "chrono_mode", "value": chrono_mode}
    )


def device_info_get_easy_timer(info: typing.Dict) -> int:
    """Get easy timer value from cached info."""
    easy_time_status = info["status"]["flags"]["is_easytimer_active"]
    return info["status"]["easytimer"]["time"] if easy_time_status else 0


@syncable
async def get_easy_timer(token: str, mac_address: str) -> int:
    """Get easy timer value, return 0 if disabled."""
    info = await device_info(token, mac_address)
    return device_info_get_easy_timer(info)


@syncable
async def set_easy_timer(token: str, mac_address: str, easy_timer: int) -> str:
    """
    Set easy timer value.
    Return response string e.g. "Command 0123456789abcdef executed successfully".
    """
    return await mqtt_command(
        token, mac_address, {"name": "easytimer", "value": easy_timer}
    )


def device_info_get_autonomy_time(info: typing.Dict) -> int:
    """Get autonomy time from cached info."""
    return info["status"]["pellet"]["autonomy_time"]


@syncable
async def get_autonomy_time(token: str, mac_address: str) -> int:
    """Get autonomy time."""
    info = await device_info(token, mac_address)
    return device_info_get_autonomy_time(info)


def device_info_get_pellet_reserve(info: typing.Dict) -> bool:
    """Get pellet reserve status from cached info."""
    return info["status"]["flags"]["is_pellet_in_reserve"]


@syncable
async def get_pellet_reserve(token: str, mac_address: str) -> bool:
    """Get pellet reserve status."""
    info = await device_info(token, mac_address)
    return device_info_get_pellet_reserve(info)


def device_info_get_serial_number(info: typing.Dict) -> str:
    """Get device serial number from cached info."""
    return info["component_info"]["motherboard"]["serial_number"]


@syncable
async def get_serial_number(token: str, mac_address: str) -> str:
    """Get device serial number."""
    info = await device_info(token, mac_address)
    return device_info_get_serial_number(info)
