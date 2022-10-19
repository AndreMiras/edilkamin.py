#!/usr/bin/env python
from edilkamin.api import device_info, set_power_off, sign_in
from edilkamin.utils import assert_env


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
