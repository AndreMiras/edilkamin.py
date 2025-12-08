"""Tests for edilkamin.ble module."""

from unittest import mock

import pytest

from edilkamin import ble


def patch_get_adapters(adapters):
    """Mock simplepyble.Adapter.get_adapters."""
    m_get_adapters = mock.Mock(return_value=adapters)
    return mock.patch("simplepyble.Adapter.get_adapters", m_get_adapters)


class TestBluetoothMacToWifiMac:
    """Tests for bluetooth_mac_to_wifi_mac function."""

    def test_converts_mac_with_colons(self):
        assert ble.bluetooth_mac_to_wifi_mac("A8:03:2A:FE:D5:0B") == "a8:03:2a:fe:d5:09"

    def test_converts_mac_without_colons(self):
        assert ble.bluetooth_mac_to_wifi_mac("A8032AFED50B") == "a8:03:2a:fe:d5:09"

    def test_handles_lowercase(self):
        assert ble.bluetooth_mac_to_wifi_mac("a8:03:2a:fe:d5:0b") == "a8:03:2a:fe:d5:09"


class TestDiscoverDevicesHelper:
    """Tests for discover_devices_helper function."""

    def test_filters_edilkamin_devices(self):
        devices = (
            {"name": "EDILKAMIN_EP", "address": "01:23:45:67:89:AB"},
            {"name": "another_device", "address": "AA:BB:CC:DD:EE:FF"},
        )
        result = ble.discover_devices_helper(devices)
        assert result == ("01:23:45:67:89:a9",)

    def test_returns_raw_mac_when_convert_false(self):
        devices = ({"name": "EDILKAMIN_EP", "address": "01:23:45:67:89:AB"},)
        result = ble.discover_devices_helper(devices, convert=False)
        assert result == ("01:23:45:67:89:AB",)

    def test_returns_empty_tuple_when_no_matches(self):
        devices = ({"name": "other_device", "address": "AA:BB:CC:DD:EE:FF"},)
        result = ble.discover_devices_helper(devices)
        assert result == ()

    def test_handles_multiple_edilkamin_devices(self):
        devices = (
            {"name": "EDILKAMIN_EP", "address": "01:23:45:67:89:AB"},
            {"name": "EDILKAMIN_EP", "address": "11:23:45:67:89:AB"},
        )
        result = ble.discover_devices_helper(devices)
        assert len(result) == 2


class TestDiscoverDevices:
    """Tests for discover_devices function."""

    @pytest.mark.parametrize(
        "convert, expected_devices",
        [
            (True, ("a8:03:2a:fe:d5:09",)),
            (False, ("A8:03:2A:FE:D5:0B",)),
        ],
    )
    def test_discover_devices(self, convert, expected_devices):
        adapters = [
            mock.Mock(
                scan_get_results=lambda: [
                    mock.Mock(
                        identifier=lambda: "EDILKAMIN_EP",
                        address=lambda: "A8:03:2A:FE:D5:0B",
                    ),
                    mock.Mock(
                        identifier=lambda: "Other device",
                        address=lambda: "00:11:22:33:44:55",
                    ),
                ]
            )
        ]
        with patch_get_adapters(adapters):
            assert ble.discover_devices(convert) == expected_devices

    def test_discover_devices_no_adapters(self):
        with patch_get_adapters([]):
            assert ble.discover_devices() == ()

    def test_discover_devices_multiple_adapters(self):
        adapter1 = mock.Mock(
            scan_get_results=lambda: [
                mock.Mock(
                    identifier=lambda: "EDILKAMIN_EP",
                    address=lambda: "AA:BB:CC:DD:EE:01",
                ),
            ]
        )
        adapter2 = mock.Mock(
            scan_get_results=lambda: [
                mock.Mock(
                    identifier=lambda: "EDILKAMIN_EP",
                    address=lambda: "AA:BB:CC:DD:EE:11",
                ),
            ]
        )
        with patch_get_adapters([adapter1, adapter2]):
            result = ble.discover_devices(convert=False)
            assert len(result) == 2
