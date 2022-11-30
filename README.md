# Edilkamin.py

[![Tests](https://github.com/AndreMiras/edilkamin.py/workflows/Tests/badge.svg)](https://github.com/AndreMiras/edilkamin.py/actions/workflows/tests.yml)
[![Coverage Status](https://coveralls.io/repos/github/AndreMiras/edilkamin.py/badge.svg?branch=main)](https://coveralls.io/github/AndreMiras/edilkamin.py?branch=main)
[![PyPI version](https://badge.fury.io/py/edilkamin.svg)](https://badge.fury.io/py/edilkamin)
[![Documentation Status](https://readthedocs.org/projects/edilkamin/badge/?version=latest)](https://edilkamin.readthedocs.io/en/latest/?badge=latest)

This is a library for the [Reverse Engineered](https://medium.com/@andre.miras/edilkamin-stove-reverse-engineering-54c8f7af6b54) "The Mind" Edilkamin API.
The Mind offers an app/API to remote control the Edilkamin pellet stoves.

## Install

```sh
pip install edilkamin[ble]
```

## Usage

```python
import edilkamin
token = edilkamin.sign_in(username, password)
mac_address = edilkamin.discover_devices()[0]
edilkamin.device_info(token, mac_address)
edilkamin.set_power_off(token, mac_address)
```
For more advanced usage read the [documentation](https://edilkamin.readthedocs.io/en/latest/).

## Tests

```sh
make test
```

## Motivations

- providing an open source web alternative
  to the [proprietary mobile app](https://play.google.com/store/apps/details?id=com.edilkamin.stufe)
- improving the interoperability (Nest, HomeAssistant...)
