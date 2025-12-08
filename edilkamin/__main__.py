#!/usr/bin/env python
"""Edilkamin CLI - Control Edilkamin pellet stoves from the command line."""

import argparse
import json
import os
import sys

from edilkamin.api import device_info, sign_in
from edilkamin.ble import discover_devices


def get_env_or_arg(
    args: argparse.Namespace, arg_name: str, env_name: str
) -> str | None:
    """Get value from command-line argument or environment variable."""
    value = getattr(args, arg_name, None)
    if value is None:
        value = os.environ.get(env_name)
    return value


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
    username = get_env_or_arg(args, "username", "EDILKAMIN_USERNAME")
    password = get_env_or_arg(args, "password", "EDILKAMIN_PASSWORD")
    mac_address = get_env_or_arg(args, "mac_address", "EDILKAMIN_MAC_ADDRESS")

    if not username:
        print(
            "Error: Username required. Use --username or set EDILKAMIN_USERNAME.",
            file=sys.stderr,
        )
        return 1
    if not password:
        print(
            "Error: Password required. Use --password or set EDILKAMIN_PASSWORD.",
            file=sys.stderr,
        )
        return 1
    if not mac_address:
        print(
            "Error: MAC address required. "
            "Use --mac-address or set EDILKAMIN_MAC_ADDRESS.",
            file=sys.stderr,
        )
        return 1

    try:
        token = sign_in(username, password)
    except Exception as e:
        print(f"Error: Authentication failed: {e}", file=sys.stderr)
        return 1

    try:
        info = device_info(token, mac_address)
    except Exception as e:
        print(f"Error: Failed to get device info: {e}", file=sys.stderr)
        return 1

    if args.pretty:
        print(json.dumps(info, indent=2))
    else:
        print(json.dumps(info))
    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="edilkamin",
        description="Control Edilkamin pellet stoves from the command line.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # discover subcommand
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
        help="Get device information",
        description="Retrieve detailed information about an Edilkamin device.",
    )
    info_parser.add_argument(
        "--username",
        "-u",
        help="Edilkamin account username (or set EDILKAMIN_USERNAME)",
    )
    info_parser.add_argument(
        "--password",
        "-p",
        help="Edilkamin account password (or set EDILKAMIN_PASSWORD)",
    )
    info_parser.add_argument(
        "--mac-address",
        "-m",
        dest="mac_address",
        help="Device MAC address (or set EDILKAMIN_MAC_ADDRESS)",
    )
    info_parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    info_parser.set_defaults(func=cmd_info)

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
