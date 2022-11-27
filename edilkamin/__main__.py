#!/usr/bin/env python
import os

from edilkamin.api import device_info, discover_devices, set_power_off, sign_in
from edilkamin.utils import assert_env


def main():
    username = assert_env("USERNAME")
    password = assert_env("PASSWORD")
    mac_address = os.environ.get("MAC_ADDRESS")
    if mac_address is None:
        mac_addresses = discover_devices()
        mac_address = mac_addresses[0] if mac_addresses else None
    assert mac_address
    token = sign_in(username, password)
    info = device_info(token, mac_address)
    print(info)
    result = set_power_off(token, mac_address)
    print(result)


if __name__ == "__main__":
    main()
