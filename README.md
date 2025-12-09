# Edilkamin.py

[![Tests](https://github.com/AndreMiras/edilkamin.py/workflows/Tests/badge.svg)](https://github.com/AndreMiras/edilkamin.py/actions/workflows/tests.yml)
[![Coverage Status](https://coveralls.io/repos/github/AndreMiras/edilkamin.py/badge.svg?branch=main)](https://coveralls.io/github/AndreMiras/edilkamin.py?branch=main)
[![PyPI version](https://badge.fury.io/py/edilkamin.svg)](https://badge.fury.io/py/edilkamin)
[![Build Docs](https://github.com/AndreMiras/edilkamin.py/actions/workflows/docs.yml/badge.svg)](https://github.com/AndreMiras/edilkamin.py/actions/workflows/docs.yml)
[![Documentation Status](https://readthedocs.org/projects/edilkamin/badge/?version=latest)](https://edilkamin.readthedocs.io/en/latest/?badge=latest)

This is a library for the [Reverse Engineered](https://medium.com/@andre.miras/edilkamin-stove-reverse-engineering-54c8f7af6b54) "The Mind" Edilkamin API.
The Mind offers an app/API to remote control the Edilkamin pellet stoves.

## Install

```sh
pip install edilkamin[ble]
```

## Usage

Both async and sync are supported seamlessly, simply use the `await` keyword for the async version.

```python
import edilkamin
token = edilkamin.sign_in(username, password)
mac_address = edilkamin.discover_devices()[0]
info = edilkamin.device_info(token, mac_address)
# or async via
# info = await edilkamin.device_info(token, mac_address)
edilkamin.set_power_off(token, mac_address)
# or async
# await edilkamin.set_power_off(token, mac_address)
```
For more advanced usage read the [documentation](https://edilkamin.readthedocs.io/en/latest/).

## API Endpoints

The library supports two backend endpoints:

### New API (Default)

```python
import edilkamin

# Uses new API endpoint by default
token = edilkamin.sign_in(username, password)
info = edilkamin.device_info(token, mac_address)
edilkamin.set_power_on(token, mac_address)
```

### Legacy API

```python
import edilkamin

# Use legacy AWS endpoint
token = edilkamin.sign_in(username, password, use_legacy_api=True)
info = edilkamin.device_info(token, mac_address, use_legacy_api=True)
edilkamin.set_power_on(token, mac_address, use_legacy_api=True)
```

For CLI, use the `--legacy` flag:

```sh
edilkamin info --username USERNAME --password PASSWORD --mac-address MAC --legacy
```

## Command Line Interface

After installation, you can control your stove directly from the terminal:

```sh
# Discover nearby Edilkamin devices via Bluetooth
edilkamin discover

# Get device information
edilkamin info --username USERNAME --password PASSWORD --mac-address MAC

# Turn the stove on
edilkamin power-on --username USERNAME --password PASSWORD --mac-address MAC

# Turn the stove off
edilkamin power-off --username USERNAME --password PASSWORD --mac-address MAC
```

You can also run via Python module:

```sh
python -m edilkamin info --username USERNAME --password PASSWORD --mac-address MAC
```

### Environment Variables

Instead of passing credentials on every command, set environment variables:

```sh
export EDILKAMIN_USERNAME="your_username"
export EDILKAMIN_PASSWORD="your_password"
export EDILKAMIN_MAC_ADDRESS="AA:BB:CC:DD:EE:FF"

# Then simply run:
edilkamin info
edilkamin power-on
edilkamin power-off
```

### Command Options

| Option | Short | Environment Variable | Description |
|--------|-------|---------------------|-------------|
| `--username` | `-u` | `EDILKAMIN_USERNAME` | Account username |
| `--password` | `-p` | `EDILKAMIN_PASSWORD` | Account password |
| `--mac-address` | `-m` | `EDILKAMIN_MAC_ADDRESS` | Device MAC address |
| `--legacy` | | `EDILKAMIN_USE_LEGACY_API` | Use legacy API (deprecated) |

Use `edilkamin --help` or `edilkamin <command> --help` for more details.

## Tests

```sh
make test
```

## Motivations

- providing an open source web alternative
  to the [proprietary mobile app](https://play.google.com/store/apps/details?id=com.edilkamin.stufe)
- improving the interoperability (Nest, HomeAssistant...)
