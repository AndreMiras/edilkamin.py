import json
from io import BytesIO
from unittest import mock

import pytest
from requests.exceptions import HTTPError
from requests.models import Response

from edilkamin import api

token = "token"
mac_address = "aabbccddeeff"


def patch_requests(method, json_response=None, status_code=200):
    response = Response()
    response.status_code = status_code
    response.raw = BytesIO(json.dumps(json_response).encode())
    m_method = mock.Mock(return_value=response)
    return mock.patch(f"edilkamin.api.requests.{method}", m_method)


def patch_requests_get(json_response=None, status_code=200):
    return patch_requests("get", json_response, status_code)


def patch_requests_put(json_response=None, status_code=200):
    return patch_requests("put", json_response, status_code)


def patch_cognito(access_token):
    m_get_user = mock.Mock()
    m_get_user._metadata = {"access_token": access_token}
    m_cognito = mock.Mock()
    m_cognito.return_value.get_user.return_value = m_get_user
    return mock.patch("edilkamin.api.Cognito", m_cognito)


def patch_get_adapters(adapters):
    m_get_adapters = mock.Mock(return_value=adapters)
    return mock.patch("simplepyble.Adapter.get_adapters", m_get_adapters)


def patch_warn():
    return mock.patch("edilkamin.api.warnings.warn")


def test_sign_in():
    username = "username"
    password = "password"
    access_token = "token"
    m_get_user = mock.Mock()
    m_get_user._metadata = {"access_token": access_token}
    with patch_cognito(access_token) as m_cognito:
        assert api.sign_in(username, password) == access_token
    assert m_cognito().authenticate.call_args_list == [mock.call(password)]
    assert m_cognito().get_user.call_args_list == [mock.call()]


@pytest.mark.parametrize(
    "convert, expected_devices",
    (
        (True, ("a8:03:2a:fe:d5:09",)),
        (False, ("A8:03:2A:FE:D5:0B",)),
    ),
)
def test_discover_devices(convert, expected_devices):
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
        assert api.discover_devices(convert) == expected_devices


def test_device_info():
    json_response = {}
    with patch_requests_get(json_response) as m_get:
        assert api.device_info(token, mac_address) == json_response
    assert m_get.call_args_list == [
        mock.call(
            "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
            "device/aabbccddeeff/info",
            headers={"Authorization": "Bearer token"},
        )
    ]


def test_device_info_error():
    """Error status should be raised."""
    json_response = {}
    status_code = 401
    with patch_requests_get(json_response, status_code) as m_get, pytest.raises(
        HTTPError, match="401 Client Error"
    ):
        api.device_info(token, mac_address)
    assert m_get.call_count == 1


def test_mqtt_command():
    json_response = '"Command 0123456789abcdef executed successfully"'
    payload = {"key": "value"}
    with patch_requests_put(json_response) as m_put:
        assert api.mqtt_command(token, mac_address, payload) == json_response
    assert m_put.call_args_list == [
        mock.call(
            "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
            "mqtt/command",
            json={"mac_address": "aabbccddeeff", "key": "value"},
            headers={"Authorization": "Bearer token"},
        )
    ]


def test_mqtt_command_error():
    """Error status should be raised."""
    json_response = {}
    status_code = 401
    payload = {"key": "value"}
    with patch_requests_put(json_response, status_code) as m_put, pytest.raises(
        HTTPError, match="401 Client Error"
    ):
        api.mqtt_command(token, mac_address, payload)
    assert m_put.call_count == 1


def test_check_connection():
    json_response = '"Command 00030529000154df executed successfully"'
    with patch_requests_put(json_response) as m_put:
        assert api.check_connection(token, mac_address) == json_response
    assert m_put.call_args_list == [
        mock.call(
            "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
            "mqtt/command",
            json={
                "mac_address": "aabbccddeeff",
                "name": "check",
            },
            headers={"Authorization": "Bearer token"},
        )
    ]


@pytest.mark.parametrize(
    "method, expected_value",
    (
        ("set_power_on", 1),
        ("set_power_off", 0),
    ),
)
def test_set_power(method, expected_value):
    json_response = '"Value is already x"'
    set_power_method = getattr(api, method)
    with patch_requests_put(json_response) as m_put:
        assert set_power_method(token, mac_address) == json_response
    assert m_put.call_args_list == [
        mock.call(
            "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
            "mqtt/command",
            json={
                "mac_address": "aabbccddeeff",
                "name": "power",
                "value": expected_value,
            },
            headers={"Authorization": "Bearer token"},
        )
    ]


@pytest.mark.parametrize(
    "power, expected_value",
    (
        (True, api.Power.ON),
        (False, api.Power.OFF),
    ),
)
def test_get_power(power, expected_value):
    json_response = {"status": {"commands": {"power": power}}}
    with patch_requests_get(json_response) as m_get:
        assert api.get_power(token, mac_address) == expected_value
    assert m_get.call_args_list == [
        mock.call(
            "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
            "device/aabbccddeeff/info",
            headers={"Authorization": "Bearer token"},
        )
    ]


def test_get_environment_temperature():
    temperature = 16.7
    json_response = {"status": {"temperatures": {"enviroment": temperature}}}
    with patch_requests_get(json_response) as m_get:
        assert api.get_environment_temperature(token, mac_address) == temperature
    assert m_get.call_count == 1


def test_get_target_temperature():
    temperature = 17.8
    json_response = {
        "nvm": {"user_parameters": {"enviroment_1_temperature": temperature}}
    }
    with patch_requests_get(json_response) as m_get:
        assert api.get_target_temperature(token, mac_address) == temperature
    assert m_get.call_count == 1


def test_set_target_temperature():
    temperature = 18.9
    json_response = "'Command 0006052500b558ab executed successfully'"
    with patch_requests_put(json_response) as m_put:
        assert (
            api.set_target_temperature(token, mac_address, temperature) == json_response
        )
    assert m_put.call_args_list == [
        mock.call(
            "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
            "mqtt/command",
            json={
                "mac_address": "aabbccddeeff",
                "name": "enviroment_1_temperature",
                "value": temperature,
            },
            headers={"Authorization": "Bearer token"},
        )
    ]


def test_get_alarm_reset():
    alarm_reset = False
    json_response = {"status": {"commands": {"alarm_reset": alarm_reset}}}
    with patch_requests_get(json_response) as m_get:
        assert api.get_alarm_reset(token, mac_address) == alarm_reset
    assert m_get.call_count == 1


def test_get_perform_cochlea_loading():
    perform_cochlea_loading = True
    json_response = {
        "status": {"commands": {"perform_cochlea_loading": perform_cochlea_loading}}
    }
    with patch_requests_get(json_response) as m_get:
        assert (
            api.get_perform_cochlea_loading(token, mac_address)
            == perform_cochlea_loading
        )
    assert m_get.call_count == 1


def test_set_perform_cochlea_loading():
    cochlea_loading = True
    json_response = "'Command 0006031c00104855 executed successfully'"
    with patch_requests_put(json_response) as m_put:
        assert (
            api.set_perform_cochlea_loading(token, mac_address, cochlea_loading)
            == json_response
        )
    assert m_put.call_args_list == [
        mock.call(
            "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
            "mqtt/command",
            json={
                "mac_address": "aabbccddeeff",
                "name": "cochlea_loading",
                "value": cochlea_loading,
            },
            headers={"Authorization": "Bearer token"},
        )
    ]


@pytest.mark.parametrize(
    "fans_number, warning, expected_speed",
    (
        (2, [], 3),
        (1, [mock.call("Only 1 fan(s) available.")], 0),
    ),
)
def test_get_fan_speed(fans_number, warning, expected_speed):
    fan_id = 2
    speed = 3
    json_response = {
        "status": {"fans": {f"fan_{fan_id}_speed": speed}},
        "nvm": {"installer_parameters": {"fans_number": fans_number}},
    }
    with patch_requests_get(json_response) as m_get, patch_warn() as m_warn:
        assert api.get_fan_speed(token, mac_address, fan_id) == expected_speed
    assert m_get.call_count == 1
    assert m_warn.call_args_list == warning


@pytest.mark.parametrize(
    "fans_number, warning, expected_return",
    (
        (2, [], "'Command executed successfully'"),
        (1, [mock.call("Only 1 fan(s) available.")], ""),
    ),
)
def test_set_fan_speed(fans_number, warning, expected_return):
    fan_id = 2
    speed = 3
    get_json_response = {"nvm": {"installer_parameters": {"fans_number": fans_number}}}
    put_json_response = "'Command executed successfully'"
    with patch_requests_get(get_json_response) as m_get, patch_warn() as m_warn:
        with patch_requests_put(put_json_response) as m_put:
            assert (
                api.set_fan_speed(token, mac_address, fan_id, speed) == expected_return
            )
    assert m_get.call_count == 1
    assert m_warn.call_args_list == warning
    assert (
        m_put.call_args_list == []
        if warning
        else [
            mock.call(
                "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
                "mqtt/command",
                json={
                    "mac_address": "aabbccddeeff",
                    "name": f"fan_{fan_id}_speed",
                    "value": speed,
                },
                headers={"Authorization": "Bearer token"},
            )
        ]
    )


def test_get_airkare():
    airkare_function = False
    json_response = {"status": {"flags": {"is_airkare_active": airkare_function}}}
    with patch_requests_get(json_response) as m_get:
        assert api.get_airkare(token, mac_address) == airkare_function
    assert m_get.call_count == 1


def test_set_airkare():
    airkare = True
    json_response = "'Command executed successfully'"
    with patch_requests_put(json_response) as m_put:
        assert api.set_airkare(token, mac_address, airkare) == json_response
    assert m_put.call_args_list == [
        mock.call(
            "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
            "mqtt/command",
            json={
                "mac_address": "aabbccddeeff",
                "name": "airkare_function",
                "value": airkare,
            },
            headers={"Authorization": "Bearer token"},
        )
    ]


def test_get_relax_mode():
    relax_mode = False
    json_response = {"status": {"flags": {"is_relax_active": relax_mode}}}
    with patch_requests_get(json_response) as m_get:
        assert api.get_relax_mode(token, mac_address) == relax_mode
    assert m_get.call_count == 1


def test_set_relax_mode():
    relax_mode = True
    json_response = "'Command executed successfully'"
    with patch_requests_put(json_response) as m_put:
        assert api.set_relax_mode(token, mac_address, relax_mode) == json_response
    assert m_put.call_args_list == [
        mock.call(
            "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
            "mqtt/command",
            json={
                "mac_address": "aabbccddeeff",
                "name": "relax_mode",
                "value": relax_mode,
            },
            headers={"Authorization": "Bearer token"},
        )
    ]


def test_get_manual_power_level():
    manual_power = 1
    json_response = {"nvm": {"user_parameters": {"manual_power": manual_power}}}
    with patch_requests_get(json_response) as m_get:
        assert api.get_manual_power_level(token, mac_address) == manual_power
    assert m_get.call_count == 1


def test_set_manual_power_level():
    power_level = 3
    json_response = "'Command executed successfully'"
    with patch_requests_put(json_response) as m_put:
        assert (
            api.set_manual_power_level(token, mac_address, power_level) == json_response
        )
    assert m_put.call_args_list == [
        mock.call(
            "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
            "mqtt/command",
            json={
                "mac_address": "aabbccddeeff",
                "name": "power_level",
                "value": power_level,
            },
            headers={"Authorization": "Bearer token"},
        )
    ]


def test_get_standby_mode():
    is_standby_active = False
    json_response = {
        "nvm": {"user_parameters": {"is_standby_active": is_standby_active}}
    }
    with patch_requests_get(json_response) as m_get:
        assert api.get_standby_mode(token, mac_address) == is_standby_active
    assert m_get.call_count == 1


@pytest.mark.parametrize(
    "is_auto, warning, expected_return",
    (
        (True, [], "'Command executed successfully'"),
        (False, [mock.call("Standby mode is only available from auto mode.")], ""),
    ),
)
def test_set_standby_mode(is_auto, warning, expected_return):
    standby_mode = True
    get_json_response = {"nvm": {"user_parameters": {"is_auto": is_auto}}}
    put_json_response = "'Command executed successfully'"
    with patch_requests_get(get_json_response) as m_get, patch_warn() as m_warn:
        with patch_requests_put(put_json_response) as m_put:
            assert (
                api.set_standby_mode(token, mac_address, standby_mode)
                == expected_return
            )
    assert m_get.call_count == 1
    assert m_warn.call_args_list == warning
    assert (
        m_put.call_args_list == []
        if warning
        else [
            mock.call(
                "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
                "mqtt/command",
                json={
                    "mac_address": "aabbccddeeff",
                    "name": "standby_mode",
                    "value": standby_mode,
                },
                headers={"Authorization": "Bearer token"},
            )
        ]
    )


def test_get_chrono_mode():
    mode = False
    json_response = {"status": {"flags": {"is_crono_active": mode}}}
    with patch_requests_get(json_response) as m_get:
        assert api.get_chrono_mode(token, mac_address) == mode
    assert m_get.call_count == 1


def test_set_chrono_mode():
    mode = True
    json_response = "'Command executed successfully'"
    with patch_requests_put(json_response) as m_put:
        assert api.set_chrono_mode(token, mac_address, mode) == json_response
    assert m_put.call_args_list == [
        mock.call(
            "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
            "mqtt/command",
            json={
                "mac_address": "aabbccddeeff",
                "name": "chrono_mode",
                "value": mode,
            },
            headers={"Authorization": "Bearer token"},
        )
    ]


@pytest.mark.parametrize(
    "mode, time, expected_return",
    (
        (False, 1234, 0),
        (True, 1234, 1234),
    ),
)
def test_get_easy_timer(mode, time, expected_return):
    json_response = {
        "status": {"flags": {"is_easytimer_active": mode}, "easytimer": {"time": time}}
    }
    with patch_requests_get(json_response) as m_get:
        assert api.get_easy_timer(token, mac_address) == expected_return
    assert m_get.call_count == 1


def test_set_easy_timer():
    mode = True
    json_response = "'Command executed successfully'"
    with patch_requests_put(json_response) as m_put:
        assert api.set_easy_timer(token, mac_address, mode) == json_response
    assert m_put.call_args_list == [
        mock.call(
            "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/"
            "mqtt/command",
            json={
                "mac_address": "aabbccddeeff",
                "name": "easytimer",
                "value": mode,
            },
            headers={"Authorization": "Bearer token"},
        )
    ]


def test_get_autonomy_time():
    time = 2100
    json_response = {"status": {"pellet": {"autonomy_time": time}}}
    with patch_requests_get(json_response) as m_get:
        assert api.get_autonomy_time(token, mac_address) == time
    assert m_get.call_count == 1


def test_get_pellet_reserve():
    mode = False
    json_response = {"status": {"flags": {"is_pellet_in_reserve": mode}}}
    with patch_requests_get(json_response) as m_get:
        assert api.get_pellet_reserve(token, mac_address) == mode
    assert m_get.call_count == 1
