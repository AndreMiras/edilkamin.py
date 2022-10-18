# Edilkamin.py

[![Tests](https://github.com/AndreMiras/edilkamin.py/workflows/Tests/badge.svg)](https://github.com/AndreMiras/edilkamin.py/actions/workflows/tests.yml)
[![PyPI version](https://badge.fury.io/py/edilkamin.svg)](https://badge.fury.io/py/edilkamin)

This is a library for the [Reverse Engineered](https://medium.com/@andre.miras/edilkamin-stove-reverse-engineering-54c8f7af6b54) "The Mind" Edilkamin API.
The Mind offers an app/API to remote control the Edilkamin pellet stoves.

## Install

```sh
pip install edilkamin
```

## Usage

```python
import edilkamin
token = edilkamin.sign_in(username, password)
edilkamin.device_info(token, mac_address)
```

## Tests
```sh
make test
```

## Motivations

- providing an open source web alternative
  to the [proprietary mobile app](https://play.google.com/store/apps/details?id=com.edilkamin.stufe)
- improving the interoperability (Nest, HomeAssistant...)

## Limitations

It seems like there's no endpoint to list stoves associated to a user.
The way the official app seem to work is by probing the stove via bluetooth.
Then cache the stove MAC address to a local database for later use.
