"""Tests for edilkamin CLI."""

import json
from unittest import mock

from edilkamin.__main__ import cmd_discover, cmd_info, create_parser, main


def make_args(**kwargs):
    """Create a namespace with default values."""
    defaults = {
        "command": None,
        "func": None,
        "raw": False,
        "username": None,
        "password": None,
        "mac_address": None,
        "pretty": False,
    }
    defaults.update(kwargs)
    return type("Args", (), defaults)()


class TestCreateParser:
    """Tests for argument parser creation."""

    def test_parser_has_discover_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["discover"])
        assert args.command == "discover"

    def test_parser_has_info_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["info"])
        assert args.command == "info"

    def test_discover_raw_flag(self):
        parser = create_parser()
        args = parser.parse_args(["discover", "--raw"])
        assert args.raw is True

    def test_info_accepts_credentials(self):
        parser = create_parser()
        args = parser.parse_args(
            [
                "info",
                "--username",
                "user",
                "--password",
                "pass",
                "--mac-address",
                "aa:bb:cc:dd:ee:ff",
            ]
        )
        assert args.username == "user"
        assert args.password == "pass"
        assert args.mac_address == "aa:bb:cc:dd:ee:ff"

    def test_info_accepts_short_flags(self):
        parser = create_parser()
        args = parser.parse_args(
            [
                "info",
                "-u",
                "user",
                "-p",
                "pass",
                "-m",
                "aa:bb:cc:dd:ee:ff",
            ]
        )
        assert args.username == "user"
        assert args.password == "pass"
        assert args.mac_address == "aa:bb:cc:dd:ee:ff"


class TestCmdDiscover:
    """Tests for discover command."""

    def test_discover_success(self, capsys):
        args = make_args(raw=False)
        with mock.patch(
            "edilkamin.__main__.discover_devices", return_value=("aa:bb:cc:dd:ee:ff",)
        ):
            result = cmd_discover(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "aa:bb:cc:dd:ee:ff" in captured.out

    def test_discover_no_devices(self, capsys):
        args = make_args(raw=False)
        with mock.patch("edilkamin.__main__.discover_devices", return_value=()):
            result = cmd_discover(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "No Edilkamin devices found" in captured.err

    def test_discover_ble_not_installed(self, capsys):
        args = make_args(raw=False)
        with mock.patch(
            "edilkamin.__main__.discover_devices",
            side_effect=ImportError("No module named 'simplepyble'"),
        ):
            result = cmd_discover(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "BLE support not installed" in captured.err

    def test_discover_raw_flag_passed(self):
        args = make_args(raw=True)
        with mock.patch(
            "edilkamin.__main__.discover_devices", return_value=("AA:BB:CC:DD:EE:FF",)
        ) as mock_discover:
            cmd_discover(args)
            mock_discover.assert_called_once_with(convert=False)


class TestCmdInfo:
    """Tests for info command."""

    def test_info_missing_username(self, capsys, monkeypatch):
        monkeypatch.delenv("EDILKAMIN_USERNAME", raising=False)
        args = make_args(
            username=None, password="pass", mac_address="aa:bb:cc:dd:ee:ff"
        )
        result = cmd_info(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Username required" in captured.err

    def test_info_missing_password(self, capsys, monkeypatch):
        monkeypatch.delenv("EDILKAMIN_PASSWORD", raising=False)
        args = make_args(
            username="user", password=None, mac_address="aa:bb:cc:dd:ee:ff"
        )
        result = cmd_info(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Password required" in captured.err

    def test_info_missing_mac(self, capsys, monkeypatch):
        monkeypatch.delenv("EDILKAMIN_MAC_ADDRESS", raising=False)
        args = make_args(username="user", password="pass", mac_address=None)
        result = cmd_info(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "MAC address required" in captured.err

    def test_info_success(self, capsys):
        args = make_args(
            username="user", password="pass", mac_address="aabbccddeeff", pretty=False
        )
        device_data = {"status": {"power": 1}}
        with mock.patch("edilkamin.__main__.sign_in", return_value="token"):
            with mock.patch("edilkamin.__main__.device_info", return_value=device_data):
                result = cmd_info(args)
        assert result == 0
        captured = capsys.readouterr()
        assert json.loads(captured.out) == device_data

    def test_info_pretty_output(self, capsys):
        args = make_args(
            username="user", password="pass", mac_address="aabbccddeeff", pretty=True
        )
        device_data = {"status": {"power": 1}}
        with mock.patch("edilkamin.__main__.sign_in", return_value="token"):
            with mock.patch("edilkamin.__main__.device_info", return_value=device_data):
                result = cmd_info(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "  " in captured.out  # Indented output

    def test_info_auth_failure(self, capsys):
        args = make_args(
            username="user", password="wrong", mac_address="aabbccddeeff", pretty=False
        )
        with mock.patch(
            "edilkamin.__main__.sign_in", side_effect=Exception("Invalid credentials")
        ):
            result = cmd_info(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Authentication failed" in captured.err

    def test_info_uses_env_vars(self, monkeypatch):
        monkeypatch.setenv("EDILKAMIN_USERNAME", "env_user")
        monkeypatch.setenv("EDILKAMIN_PASSWORD", "env_pass")
        monkeypatch.setenv("EDILKAMIN_MAC_ADDRESS", "aabbccddeeff")
        args = make_args(username=None, password=None, mac_address=None, pretty=False)
        with mock.patch(
            "edilkamin.__main__.sign_in", return_value="token"
        ) as mock_sign_in:
            with mock.patch("edilkamin.__main__.device_info", return_value={}):
                cmd_info(args)
        mock_sign_in.assert_called_once_with("env_user", "env_pass")

    def test_info_with_buffer_response(self, capsys):
        """CLI should display decompressed buffer data as JSON."""
        args = make_args(
            username="user", password="pass", mac_address="aabbccddeeff", pretty=False
        )

        # Expected output after decompression (device_info handles decompression)
        expected_output = {
            "component_info": {
                "motherboard": {"serial_number": "ABC123", "version": "1.0"}
            },
            "mac_address": "aabbccddeeff",
            "pk": 1,
        }

        with mock.patch("edilkamin.__main__.sign_in", return_value="token"):
            with mock.patch(
                "edilkamin.__main__.device_info", return_value=expected_output
            ):
                result = cmd_info(args)

        assert result == 0
        captured = capsys.readouterr()
        output_json = json.loads(captured.out)

        # Verify decompressed data is displayed correctly
        assert output_json == expected_output
        assert output_json["component_info"]["motherboard"]["serial_number"] == "ABC123"


class TestMain:
    """Tests for main entry point."""

    def test_no_command_shows_help(self, capsys):
        with mock.patch("sys.argv", ["edilkamin"]):
            result = main()
        assert result == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower() or "edilkamin" in captured.out
