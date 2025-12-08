"""Bluetooth Low Energy (BLE) functions for Edilkamin device discovery."""

import typing

# Import format_mac from api to avoid duplication
from edilkamin.api import format_mac

# Re-export for convenience
__all__ = [
    "bluetooth_mac_to_wifi_mac",
    "discover_devices",
    "discover_devices_helper",
    "format_mac",
]


def bluetooth_mac_to_wifi_mac(mac: str) -> str:
    """
    Convert Bluetooth MAC address to WiFi MAC address.

    Edilkamin devices have BLE MAC addresses that are offset by +2 from their WiFi MAC.

    >>> bluetooth_mac_to_wifi_mac("A8:03:2A:FE:D5:0B")
    'a8:03:2a:fe:d5:09'
    """
    mac = format_mac(mac)
    mac_int = int(mac, 16)
    mac_wifi_int = mac_int - 2
    mac_wifi = "{:012x}".format(mac_wifi_int)
    return ":".join(mac_wifi[i : i + 2] for i in range(0, len(mac_wifi), 2))


def discover_devices_helper(
    devices: typing.Tuple[typing.Dict, ...], convert: bool = True
) -> typing.Tuple[str, ...]:
    """
    Filter discovered Bluetooth devices for Edilkamin devices.

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


def discover_devices(convert: bool = True) -> typing.Tuple[str, ...]:
    """
    Discover Edilkamin devices using Bluetooth.

    Scans for nearby Edilkamin devices and returns their MAC addresses.
    By default, returns WiFi MAC addresses (used for API calls).
    Set convert=False to get raw Bluetooth MAC addresses.

    Requires the 'ble' extra: pip install edilkamin[ble]

    Returns:
        Tuple of MAC address strings in format 'aa:bb:cc:dd:ee:ff'
    """
    import simplepyble

    devices: typing.Tuple[typing.Dict, ...] = ()
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
