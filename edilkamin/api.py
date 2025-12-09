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


def sign_in(username: str, password: str, use_legacy_api: bool = False) -> str:
    """Sign in and return token.

    Args:
        username: Edilkamin account username
        password: Edilkamin account password
        use_legacy_api: If True, use old AWS API and access_token.
                       If False (default), use new API and id_token.

    Returns:
        JWT token for API authentication
    """
    cognito = Cognito(constants.USER_POOL_ID, constants.CLIENT_ID, username=username)
    cognito.authenticate(password)
    user = cognito.get_user()
    # New API uses id_token, old API uses access_token
    token_key = "access_token" if use_legacy_api else "id_token"
    return user._metadata[token_key]


def format_mac(mac: str):
    return mac.replace(":", "").lower()


@syncable
async def device_info(
    token: str, mac: str, use_legacy_api: bool = False
) -> typing.Dict:
    """Retrieve device info for a given MAC address in the format `aabbccddeeff`.

    Automatically decompresses any gzip-compressed Buffer fields in the response.

    Args:
        token: JWT token from sign_in()
        mac: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    headers = get_headers(token)
    mac = format_mac(mac)
    url = get_endpoint(f"device/{mac}/info", use_legacy_api)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        raw_data = response.json()
        # Process response to decompress any Buffer fields
        return process_response(raw_data)


@syncable
async def mqtt_command(
    token: str, mac_address: str, payload: typing.Dict, use_legacy_api: bool = False
) -> str:
    """Send a MQTT command to the device identified with the MAC address.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        payload: Command payload
        use_legacy_api: If True, use old AWS API URL

    Returns:
        Response string from API
    """
    headers = get_headers(token)
    url = get_endpoint("mqtt/command", use_legacy_api)
    data = {"mac_address": format_mac(mac_address), **payload}
    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()


@syncable
async def check_connection(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> str:
    """Check if the token is still valid.

    Returns "Command 00030529000154df executed successfully" on success.
    Raises an `HTTPError` exception otherwise.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    return await mqtt_command(token, mac_address, {"name": "check"}, use_legacy_api)


@syncable
async def set_power(
    token: str, mac_address: str, power: Power, use_legacy_api: bool = False
) -> str:
    """Set device power.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        power: Power.ON or Power.OFF
        use_legacy_api: If True, use old AWS API URL

    Returns:
        Response string e.g. "Command 0123456789abcdef executed successfully"
    """
    return await mqtt_command(
        token, mac_address, {"name": "power", "value": power.value}, use_legacy_api
    )


def device_info_get_power(info: typing.Dict) -> Power:
    """Get device current power value from cached info."""
    return Power(info["status"]["commands"]["power"])


@syncable
async def get_power(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> Power:
    """Get device current power value.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_power(info)


@syncable
async def set_power_on(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> str:
    """Turn on device.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    return await set_power(token, mac_address, Power.ON, use_legacy_api)


@syncable
async def set_power_off(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> str:
    """Turn off device.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    return await set_power(token, mac_address, Power.OFF, use_legacy_api)


def device_info_get_alarm_reset(info: typing.Dict) -> bool:
    """Get alarm reset value from cached info."""
    return info["status"]["commands"]["alarm_reset"]


@syncable
async def get_alarm_reset(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> bool:
    """Get alarm reset value.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_alarm_reset(info)


def device_info_get_perform_cochlea_loading(info: typing.Dict) -> bool:
    """Get perform cochlea loading state from cached info."""
    return info["status"]["commands"]["perform_cochlea_loading"]


@syncable
async def get_perform_cochlea_loading(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> bool:
    """Get perform cochlea loading state.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_perform_cochlea_loading(info)


@syncable
async def set_perform_cochlea_loading(
    token: str, mac_address: str, value: bool, use_legacy_api: bool = False
) -> str:
    """Set the perform cochlea loading value.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        value: True to enable, False to disable
        use_legacy_api: If True, use old AWS API URL
    """
    payload = {"name": "cochlea_loading", "value": bool(value)}
    return await mqtt_command(token, mac_address, payload, use_legacy_api)


def device_info_get_environment_temperature(info: typing.Dict) -> int:
    """Get environment temperature value from cached info."""
    return info["status"]["temperatures"]["enviroment"]


@syncable
async def get_environment_temperature(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> Power:
    """Get environment temperature coming from sensor.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_environment_temperature(info)


def device_info_get_target_temperature(info: typing.Dict) -> int:
    """Get target temperature value from cached info."""
    return info["nvm"]["user_parameters"]["enviroment_1_temperature"]


@syncable
async def get_target_temperature(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> Power:
    """Get target temperature value.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_target_temperature(info)


@syncable
async def set_target_temperature(
    token: str, mac_address: str, temperature: int, use_legacy_api: bool = False
) -> str:
    """Set target temperature in degree.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        temperature: Target temperature in degrees
        use_legacy_api: If True, use old AWS API URL

    Returns:
        Response string e.g. "Command 0006052500b558ab executed successfully"
    """
    payload = {"name": "enviroment_1_temperature", "value": temperature}
    return await mqtt_command(token, mac_address, payload, use_legacy_api)


def valid_fan_id_or_warning(info: typing.Dict, fan_id):
    fans_number = info["nvm"]["installer_parameters"]["fans_number"]
    if fans_number < fan_id:
        warnings.warn(f"Only {fans_number} fan(s) available.", stacklevel=2)
    return fans_number >= fan_id


def device_info_get_fan_speed(info: typing.Dict, fan_id: int) -> int:
    """Get fan id speed value from cached info."""
    return info["status"]["fans"][f"fan_{fan_id}_speed"]


@syncable
async def get_fan_speed(
    token: str, mac_address: str, fan_id: int, use_legacy_api: bool = False
) -> int:
    """Get fan id speed value.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        fan_id: Fan ID to query
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    if not valid_fan_id_or_warning(info, fan_id):
        return 0
    return device_info_get_fan_speed(info, fan_id)


@syncable
async def set_fan_speed(
    token: str, mac_address: str, fan_id: int, speed: int, use_legacy_api: bool = False
) -> str:
    """Set fan id speed.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        fan_id: Fan ID to set
        speed: Speed value
        use_legacy_api: If True, use old AWS API URL

    Returns:
        Response string e.g. "Command 0123456789abcdef executed successfully"
    """
    info = await device_info(token, mac_address, use_legacy_api)
    if not valid_fan_id_or_warning(info, fan_id):
        return ""
    payload = {"name": f"fan_{fan_id}_speed", "value": speed}
    return await mqtt_command(token, mac_address, payload, use_legacy_api)


def device_info_get_airkare(info: typing.Dict) -> bool:
    """Get airkare status from cached info."""
    return info["status"]["flags"]["is_airkare_active"]


@syncable
async def get_airkare(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> bool:
    """Get airkare status.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_airkare(info)


@syncable
async def set_airkare(
    token: str, mac_address: str, airkare: bool, use_legacy_api: bool = False
) -> str:
    """Set airkare.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        airkare: True to enable, False to disable
        use_legacy_api: If True, use old AWS API URL

    Returns:
        Response string e.g. "Command 0123456789abcdef executed successfully"
    """
    payload = {"name": "airkare_function", "value": airkare}
    return await mqtt_command(token, mac_address, payload, use_legacy_api)


def device_info_get_relax_mode(info: typing.Dict) -> bool:
    """Get relax mode status from cached info."""
    return info["status"]["flags"]["is_relax_active"]


@syncable
async def get_relax_mode(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> bool:
    """Get relax mode status.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_relax_mode(info)


@syncable
async def set_relax_mode(
    token: str, mac_address: str, relax_mode: bool, use_legacy_api: bool = False
) -> str:
    """Set relax mode.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        relax_mode: True to enable, False to disable
        use_legacy_api: If True, use old AWS API URL

    Returns:
        Response string e.g. "Command 0123456789abcdef executed successfully"
    """
    payload = {"name": "relax_mode", "value": relax_mode}
    return await mqtt_command(token, mac_address, payload, use_legacy_api)


def device_info_get_manual_power_level(info: typing.Dict) -> int:
    """Get manual power level value from cached info."""
    return info["nvm"]["user_parameters"]["manual_power"]


@syncable
async def get_manual_power_level(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> int:
    """Get manual power level value.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_manual_power_level(info)


@syncable
async def set_manual_power_level(
    token: str, mac_address: str, manual_power_level: int, use_legacy_api: bool = False
) -> str:
    """Set manual power level value.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        manual_power_level: Power level to set
        use_legacy_api: If True, use old AWS API URL

    Returns:
        Response string e.g. "Command 0123456789abcdef executed successfully"
    """
    payload = {"name": "power_level", "value": manual_power_level}
    return await mqtt_command(token, mac_address, payload, use_legacy_api)


def device_info_get_standby_mode(info: typing.Dict) -> bool:
    """Get standby mode status from cached info."""
    return info["nvm"]["user_parameters"]["is_standby_active"]


@syncable
async def get_standby_mode(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> bool:
    """Get standby mode status.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_standby_mode(info)


@syncable
async def set_standby_mode(
    token: str, mac_address: str, standby_mode: bool, use_legacy_api: bool = False
) -> str:
    """Set standby mode.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        standby_mode: True to enable, False to disable
        use_legacy_api: If True, use old AWS API URL

    Returns:
        Response string e.g. "Command 0123456789abcdef executed successfully"
    """
    info = await device_info(token, mac_address, use_legacy_api)
    is_auto = info["nvm"]["user_parameters"]["is_auto"]
    if not is_auto:
        warnings.warn("Standby mode is only available from auto mode.", stacklevel=2)
        return ""
    payload = {"name": "standby_mode", "value": standby_mode}
    return await mqtt_command(token, mac_address, payload, use_legacy_api)


def device_info_get_chrono_mode(info: typing.Dict) -> bool:
    """Get chrono mode status from cached info."""
    return info["status"]["flags"]["is_crono_active"]


@syncable
async def get_chrono_mode(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> bool:
    """Get chrono mode status.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_chrono_mode(info)


@syncable
async def set_chrono_mode(
    token: str, mac_address: str, chrono_mode: bool, use_legacy_api: bool = False
) -> str:
    """Set chrono mode.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        chrono_mode: True to enable, False to disable
        use_legacy_api: If True, use old AWS API URL

    Returns:
        Response string e.g. "Command 0123456789abcdef executed successfully"
    """
    payload = {"name": "chrono_mode", "value": chrono_mode}
    return await mqtt_command(token, mac_address, payload, use_legacy_api)


def device_info_get_easy_timer(info: typing.Dict) -> int:
    """Get easy timer value from cached info."""
    easy_time_status = info["status"]["flags"]["is_easytimer_active"]
    return info["status"]["easytimer"]["time"] if easy_time_status else 0


@syncable
async def get_easy_timer(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> int:
    """Get easy timer value, return 0 if disabled.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_easy_timer(info)


@syncable
async def set_easy_timer(
    token: str, mac_address: str, easy_timer: int, use_legacy_api: bool = False
) -> str:
    """Set easy timer value.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        easy_timer: Timer value to set
        use_legacy_api: If True, use old AWS API URL

    Returns:
        Response string e.g. "Command 0123456789abcdef executed successfully"
    """
    return await mqtt_command(
        token, mac_address, {"name": "easytimer", "value": easy_timer}, use_legacy_api
    )


def device_info_get_autonomy_time(info: typing.Dict) -> int:
    """Get autonomy time from cached info."""
    return info["status"]["pellet"]["autonomy_time"]


@syncable
async def get_autonomy_time(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> int:
    """Get autonomy time.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_autonomy_time(info)


def device_info_get_pellet_reserve(info: typing.Dict) -> bool:
    """Get pellet reserve status from cached info."""
    return info["status"]["flags"]["is_pellet_in_reserve"]


@syncable
async def get_pellet_reserve(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> bool:
    """Get pellet reserve status.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_pellet_reserve(info)


def device_info_get_serial_number(info: typing.Dict) -> str:
    """Get device serial number from cached info.

    Note: Serial numbers may contain binary/control characters from device
    firmware. Use serial_number_hex() or serial_number_display() for safe
    string representations.
    """
    return info["component_info"]["motherboard"]["serial_number"]


@syncable
async def get_serial_number(
    token: str, mac_address: str, use_legacy_api: bool = False
) -> str:
    """Get device serial number.

    Note: Serial numbers may contain binary/control characters from device
    firmware. Use serial_number_hex() or serial_number_display() for safe
    string representations.

    Args:
        token: JWT token from sign_in()
        mac_address: Device MAC address
        use_legacy_api: If True, use old AWS API URL
    """
    info = await device_info(token, mac_address, use_legacy_api)
    return device_info_get_serial_number(info)


def serial_number_hex(serial: str) -> str:
    """Convert serial number to hex string for safe storage/display.

    Serial numbers from Edilkamin devices may contain binary control
    characters. This function converts the serial to a hex string that
    is safe to store, display, and transmit.

    Args:
        serial: Raw serial number string (may contain binary data)

    Returns:
        Hex-encoded string (e.g., "1a435d374a5353...")

    Example:
        >>> raw = "\x1aC]7JSS   L\x19\x1a\x0c\xff"  # Example with control chars
        >>> hex_serial = serial_number_hex(raw)
        >>> print(hex_serial)
        1a435d374a53532020204c191a0cc3bf
    """
    return serial.encode("utf-8", errors="surrogateescape").hex()


def serial_number_from_hex(hex_serial: str) -> str:
    """Convert hex-encoded serial number back to raw string.

    Args:
        hex_serial: Hex-encoded serial string

    Returns:
        Raw serial number string

    Example:
        >>> raw = serial_number_from_hex("1a435d374a53532020204c191a0cc3bf")
    """
    return bytes.fromhex(hex_serial).decode("utf-8", errors="surrogateescape")


def serial_number_display(serial: str) -> str:
    """Get a display-safe version of the serial number.

    Removes non-printable characters and strips whitespace, returning
    only the human-readable portion of the serial number.

    Args:
        serial: Raw serial number string (may contain binary data)

    Returns:
        Printable characters only, stripped of leading/trailing whitespace

    Example:
        >>> raw = "\x1aC]7JSS   L\x19\x1a\x0c\xff"  # Contains control chars
        >>> display = serial_number_display(raw)
        >>> print(display)
        C]7JSS L
    """
    # Keep only printable ASCII characters (0x20-0x7E) and common whitespace
    printable = "".join(c if (0x20 <= ord(c) <= 0x7E) else " " for c in serial)
    # Collapse multiple spaces and strip
    return " ".join(printable.split())


@syncable
async def register_device(
    token: str,
    mac_address: str,
    device_name: str,
    device_room: str,
    serial_number: str,
    use_legacy_api: bool = False,
) -> typing.Dict:
    """Register/associate a device with the user account.

    This function registers a new device or updates an existing registration.
    The API performs an upsert operation (returns 201 for both new and
    existing devices).

    Note: The API accepts serial numbers in any format (raw, hex-encoded,
    or base64-encoded). For consistency, you can use the raw serial from
    get_serial_number() or a hex-encoded version from serial_number_hex().

    Args:
        token: OAuth access token from sign_in()
        mac_address: Device WiFi MAC address (e.g., "aa:bb:cc:dd:ee:ff")
        device_name: User-provided name for the device
        device_room: User-provided room name
        serial_number: Device serial number (from get_serial_number() or
            manual entry from device label)
        use_legacy_api: If True, use old AWS API URL

    Returns:
        API response dict with macAddress, deviceName, deviceRoom

    Raises:
        httpx.HTTPStatusError: If registration fails

    Example:
        >>> token = sign_in("user@example.com", "password")
        >>> # Get serial from existing device
        >>> serial = get_serial_number(token, "aa:bb:cc:dd:ee:ff")
        >>> # Or use hex-encoded for safety
        >>> serial_hex = serial_number_hex(serial)
        >>> register_device(
        ...     token,
        ...     "aa:bb:cc:dd:ee:ff",
        ...     "Living Room Stove",
        ...     "Living Room",
        ...     serial_hex
        ... )
    """
    headers = get_headers(token)
    url = get_endpoint("device", use_legacy_api)
    data = {
        "macAddress": format_mac(mac_address),
        "deviceName": device_name,
        "deviceRoom": device_room,
        "serialNumber": serial_number,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()


@syncable
async def edit_device(
    token: str,
    mac_address: str,
    device_name: str,
    device_room: str,
    use_legacy_api: bool = False,
) -> typing.Dict:
    """Update device name and room.

    Unlike register_device(), this does not require the serial number.

    Args:
        token: OAuth access token from sign_in()
        mac_address: Device WiFi MAC address (e.g., "aa:bb:cc:dd:ee:ff")
        device_name: New name for the device
        device_room: New room name
        use_legacy_api: If True, use old AWS API URL

    Returns:
        API response dict

    Raises:
        httpx.HTTPStatusError: If update fails
    """
    headers = get_headers(token)
    mac = format_mac(mac_address)
    url = get_endpoint(f"device/{mac}", use_legacy_api)
    data = {
        "deviceName": device_name,
        "deviceRoom": device_room,
    }
    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
