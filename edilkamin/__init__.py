#!/usr/bin/env python
import os

import requests
from pycognito import Cognito

BACKEND_URL = "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"

USER_POOL_ID = "eu-central-1_BYmQ2VBlo"
CLIENT_ID = "7sc1qltkqobo3ddqsk4542dg2h"


def sign_in(username, password):
    cognito = Cognito(USER_POOL_ID, CLIENT_ID, username=username)
    cognito.authenticate(password)
    user = cognito.get_user()
    return user._metadata["access_token"]


def device_info(token: str, mac: str):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BACKEND_URL}device/{mac}/info", headers=headers)
    response.raise_for_status()
    return response.json()


def main():
    assert (username := os.environ.get("USERNAME"))
    assert (password := os.environ.get("PASSWORD"))
    assert (mac_address := os.environ.get("MAC_ADDRESS"))
    user = sign_in(username, password)
    token = user._metadata["access_token"]
    info = device_info(token, mac_address)


if __name__ == "__main__":
    main()
