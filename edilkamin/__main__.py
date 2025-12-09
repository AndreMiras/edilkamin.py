#!/usr/bin/env python
"""Edilkamin CLI - Control Edilkamin pellet stoves from the command line."""

import argparse
import json
import os
import sys
import warnings

from edilkamin.api import device_info, set_power_off, set_power_on, sign_in
from edilkamin.ble import discover_devices


def cli_error(message: str) -> int:
    """Print error message to stderr and return exit code 1."""
    print(f"Error: {message}", file=sys.stderr)
    return 1


def get_env_or_arg(
    args: argparse.Namespace, arg_name: str, env_name: str
) -> str | None:
    """Get value from command-line argument or environment variable."""
    value = getattr(args, arg_name, None)
    if value is None:
        value = os.environ.get(env_name)
    return value


def get_use_legacy_api(args: argparse.Namespace) -> bool:
    """Get legacy API setting from args or environment.

    Returns True if legacy API should be used.
    """
    # CLI flag takes precedence
    if getattr(args, "legacy", False):
        return True
    # Fall back to environment variable
    env_value = os.environ.get("EDILKAMIN_USE_LEGACY_API", "").lower()
    return env_value in ("1", "true", "yes")


def get_credentials(
    args: argparse.Namespace,
) -> tuple[str, str, str] | int:
    """Extract and validate credentials from args or environment.

    Returns (username, password, mac_address) tuple on success, or error exit code.
    """
    username = get_env_or_arg(args, "username", "EDILKAMIN_USERNAME")
    password = get_env_or_arg(args, "password", "EDILKAMIN_PASSWORD")
    mac_address = get_env_or_arg(args, "mac_address", "EDILKAMIN_MAC_ADDRESS")

    if not username:
        return cli_error("Username required. Use --username or set EDILKAMIN_USERNAME.")
    if not password:
        return cli_error("Password required. Use --password or set EDILKAMIN_PASSWORD.")
    if not mac_address:
        return cli_error(
            "MAC address required. Use --mac-address or set EDILKAMIN_MAC_ADDRESS."
        )

    return username, password, mac_address


def authenticate(
    username: str, password: str, use_legacy_api: bool = False
) -> str | int:
    """Sign in and return token, or error exit code on failure."""
    if use_legacy_api:
        warnings.warn(
            "Using legacy API endpoint (deprecated). "
            "The --legacy flag will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
    try:
        return sign_in(username, password, use_legacy_api)
    except Exception as e:
        return cli_error(f"Authentication failed: {e}")


def cmd_discover(args: argparse.Namespace) -> int:
    """Handle the 'discover' subcommand."""
    try:
        devices = discover_devices(convert=not args.raw)
    except ImportError:
        print(
            "Error: BLE support not installed. "
            "Install with: pip install edilkamin[ble]",
            file=sys.stderr,
        )
        return 1

    if not devices:
        print("No Edilkamin devices found.", file=sys.stderr)
        return 1

    for mac in devices:
        print(mac)
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Handle the 'info' subcommand."""
    creds = get_credentials(args)
    if isinstance(creds, int):
        return creds
    username, password, mac_address = creds
    use_legacy_api = get_use_legacy_api(args)

    token = authenticate(username, password, use_legacy_api)
    if isinstance(token, int):
        return token

    try:
        info = device_info(token, mac_address, use_legacy_api)
    except Exception as e:
        return cli_error(f"Failed to get device info: {e}")

    if args.pretty:
        print(json.dumps(info, indent=2))
    else:
        print(json.dumps(info))
    return 0


def cmd_power_on(args: argparse.Namespace) -> int:
    """Handle the 'power-on' subcommand."""
    creds = get_credentials(args)
    if isinstance(creds, int):
        return creds
    username, password, mac_address = creds
    use_legacy_api = get_use_legacy_api(args)

    token = authenticate(username, password, use_legacy_api)
    if isinstance(token, int):
        return token

    try:
        result = set_power_on(token, mac_address, use_legacy_api)
        print(result)
        return 0
    except Exception as e:
        return cli_error(f"Failed to turn on device: {e}")


def cmd_power_off(args: argparse.Namespace) -> int:
    """Handle the 'power-off' subcommand."""
    creds = get_credentials(args)
    if isinstance(creds, int):
        return creds
    username, password, mac_address = creds
    use_legacy_api = get_use_legacy_api(args)

    token = authenticate(username, password, use_legacy_api)
    if isinstance(token, int):
        return token

    try:
        result = set_power_off(token, mac_address, use_legacy_api)
        print(result)
        return 0
    except Exception as e:
        return cli_error(f"Failed to turn off device: {e}")


def create_auth_parser() -> argparse.ArgumentParser:
    """Create a parent parser with common authentication arguments."""
    auth_parser = argparse.ArgumentParser(add_help=False)
    auth_parser.add_argument(
        "--username",
        "-u",
        help="Edilkamin account username (or set EDILKAMIN_USERNAME)",
    )
    auth_parser.add_argument(
        "--password",
        "-p",
        help="Edilkamin account password (or set EDILKAMIN_PASSWORD)",
    )
    auth_parser.add_argument(
        "--mac-address",
        "-m",
        dest="mac_address",
        help="Device MAC address (or set EDILKAMIN_MAC_ADDRESS)",
    )
    auth_parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use legacy API endpoint (deprecated, or set EDILKAMIN_USE_LEGACY_API)",
    )
    return auth_parser


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="edilkamin",
        description="Control Edilkamin pellet stoves from the command line.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Parent parser for authenticated commands
    auth_parser = create_auth_parser()

    # discover subcommand (no auth required)
    discover_parser = subparsers.add_parser(
        "discover",
        help="Discover Edilkamin devices via Bluetooth",
        description="Scan for nearby Edilkamin devices using Bluetooth Low Energy.",
    )
    discover_parser.add_argument(
        "--raw",
        action="store_true",
        help="Show raw Bluetooth MAC addresses instead of WiFi MAC addresses",
    )
    discover_parser.set_defaults(func=cmd_discover)

    # info subcommand
    info_parser = subparsers.add_parser(
        "info",
        parents=[auth_parser],
        help="Get device information",
        description="Retrieve detailed information about an Edilkamin device.",
    )
    info_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    info_parser.set_defaults(func=cmd_info)

    # power-on subcommand
    power_on_parser = subparsers.add_parser(
        "power-on",
        parents=[auth_parser],
        help="Turn on device",
        description="Turn on an Edilkamin device.",
    )
    power_on_parser.set_defaults(func=cmd_power_on)

    # power-off subcommand
    power_off_parser = subparsers.add_parser(
        "power-off",
        parents=[auth_parser],
        help="Turn off device",
        description="Turn off an Edilkamin device.",
    )
    power_off_parser.set_defaults(func=cmd_power_off)

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
