from unittest import mock

import pytest
from httpx import HTTPStatusError, Response
from respx import Router

from edilkamin import api

DEVICE_INFO_URL = "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"

MQTT_COMMAND_URL = (
    "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
)

token = "token"
mac_address = "aabbccddeeff"


def patch_cognito(access_token):
    m_get_user = mock.Mock()
    m_get_user._metadata = {"access_token": access_token}
    m_cognito = mock.Mock()
    m_cognito.access_token = access_token
    m_cognito.return_value.get_user.return_value = m_get_user
    return mock.patch("edilkamin.api.Cognito", m_cognito)


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


def test_device_info(respx_mock: Router):
    json_response = {}

    respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)

    assert api.device_info(token, mac_address) == json_response


def test_device_info_with_buffer_response(respx_mock: Router):
    """device_info should automatically decompress Buffer fields."""
    import gzip
    import json

    component_data = {"motherboard": {"serial_number": "ABC123"}}
    nvm_data = {"user_parameters": {"enviroment_1_temperature": 20}}
    status_data = {"commands": {"power": 1}}

    json_response = {
        "component_info": {
            "type": "Buffer",
            "data": list(gzip.compress(json.dumps(component_data).encode())),
        },
        "nvm": {
            "type": "Buffer",
            "data": list(gzip.compress(json.dumps(nvm_data).encode())),
        },
        "status": {
            "type": "Buffer",
            "data": list(gzip.compress(json.dumps(status_data).encode())),
        },
        "mac_address": "aabbccddeeff",
        "pk": 1,
    }

    respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)

    result = api.device_info(token, mac_address)

    # Verify buffers were decompressed
    assert result["component_info"] == component_data
    assert result["nvm"] == nvm_data
    assert result["status"] == status_data
    # Plain fields should remain unchanged
    assert result["mac_address"] == "aabbccddeeff"
    assert result["pk"] == 1


def test_device_info_backward_compatible_plain_json(respx_mock: Router):
    """device_info should still work with plain JSON responses."""
    json_response = {
        "component_info": {"motherboard": {"serial_number": "ABC123"}},
        "nvm": {"user_parameters": {"enviroment_1_temperature": 20}},
        "status": {"commands": {"power": 1}},
        "mac_address": "aabbccddeeff",
        "pk": 1,
    }

    respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)

    result = api.device_info(token, mac_address)

    # Plain JSON should pass through unchanged
    assert result == json_response


def test_get_serial_number_with_buffer_response(respx_mock: Router):
    """get_serial_number should work with buffer responses."""
    import gzip
    import json

    serial = "XYZ789"
    component_data = {"motherboard": {"serial_number": serial}}

    json_response = {
        "component_info": {
            "type": "Buffer",
            "data": list(gzip.compress(json.dumps(component_data).encode())),
        }
    }

    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)

    result = api.get_serial_number(token, mac_address)

    assert result == serial
    assert route.called


def test_get_power_with_buffer_response(respx_mock: Router):
    """get_power should work with buffer responses."""
    import gzip
    import json

    power = True
    status_data = {"commands": {"power": power}}

    json_response = {
        "status": {
            "type": "Buffer",
            "data": list(gzip.compress(json.dumps(status_data).encode())),
        }
    }

    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)

    result = api.get_power(token, mac_address)

    assert result == api.Power.ON
    assert route.called


def test_get_target_temperature_with_buffer_response(respx_mock: Router):
    """get_target_temperature should work with buffer responses."""
    import gzip
    import json

    temperature = 22.5
    nvm_data = {"user_parameters": {"enviroment_1_temperature": temperature}}

    json_response = {
        "nvm": {
            "type": "Buffer",
            "data": list(gzip.compress(json.dumps(nvm_data).encode())),
        }
    }

    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)

    result = api.get_target_temperature(token, mac_address)

    assert result == temperature
    assert route.called


def test_device_info_error(respx_mock: Router):
    """Error status should be raised."""

    respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=401)

    with pytest.raises(HTTPStatusError, match="Client error '401 Unauthorized'"):
        api.device_info(token, mac_address)


def test_mqtt_command(respx_mock: Router):
    json_response = '"Command 0123456789abcdef executed successfully"'
    payload = {"key": "value"}

    respx_mock.put(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
    ) % Response(status_code=200, json=json_response)

    assert api.mqtt_command(token, mac_address, payload) == json_response


def test_mqtt_command_error(respx_mock: Router):
    """Error status should be raised."""
    json_response = {}
    status_code = 401
    payload = {"key": "value"}

    respx_mock.put(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
    ) % Response(status_code=status_code, json=json_response)
    with pytest.raises(HTTPStatusError, match="Client error '401 Unauthorized'"):
        api.mqtt_command(token, mac_address, payload)


def test_check_connection(respx_mock: Router):
    json_response = '"Command 00030529000154df executed successfully"'

    respx_mock.put(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
    ) % Response(status_code=200, json=json_response)

    assert api.check_connection(token, mac_address) == json_response


@pytest.mark.parametrize(
    "method, expected_value",
    (
        ("set_power_on", 1),
        ("set_power_off", 0),
    ),
)
def test_set_power(method, expected_value, respx_mock: Router):
    json_response = '"Value is already x"'
    set_power_method = getattr(api, method)

    respx_mock.put(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
    ) % Response(status_code=200, json=json_response)

    assert set_power_method(token, mac_address) == json_response


@pytest.mark.parametrize(
    "power, expected_value",
    (
        (True, api.Power.ON),
        (False, api.Power.OFF),
    ),
)
def test_get_power(power, expected_value, respx_mock: Router):
    json_response = {"status": {"commands": {"power": power}}}
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_power(token, mac_address) == expected_value
    assert route.called


def test_get_environment_temperature(respx_mock: Router):
    temperature = 16.7
    json_response = {"status": {"temperatures": {"enviroment": temperature}}}
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_environment_temperature(token, mac_address) == temperature
    assert route.called


def test_get_target_temperature(respx_mock: Router):
    temperature = 17.8
    json_response = {
        "nvm": {"user_parameters": {"enviroment_1_temperature": temperature}}
    }
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_target_temperature(token, mac_address) == temperature
    assert route.called


def test_set_target_temperature(respx_mock: Router):
    temperature = 18.9
    json_response = "'Command 0006052500b558ab executed successfully'"
    route = respx_mock.put(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
    ) % Response(status_code=200, json=json_response)
    assert api.set_target_temperature(token, mac_address, temperature) == json_response
    assert route.called


def test_get_alarm_reset(respx_mock: Router):
    alarm_reset = False
    json_response = {"status": {"commands": {"alarm_reset": alarm_reset}}}
    respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_alarm_reset(token, mac_address) == alarm_reset


def test_get_perform_cochlea_loading(respx_mock: Router):
    perform_cochlea_loading = True
    json_response = {
        "status": {"commands": {"perform_cochlea_loading": perform_cochlea_loading}}
    }
    respx_mock.get(DEVICE_INFO_URL) % Response(status_code=200, json=json_response)
    assert (
        api.get_perform_cochlea_loading(token, mac_address) == perform_cochlea_loading
    )


def test_set_perform_cochlea_loading(respx_mock: Router):
    cochlea_loading = True
    json_response = "'Command 0006031c00104855 executed successfully'"
    route = respx_mock.put(MQTT_COMMAND_URL) % Response(
        status_code=200, json=json_response
    )
    assert (
        api.set_perform_cochlea_loading(token, mac_address, cochlea_loading)
        == json_response
    )
    assert route.called


@pytest.mark.parametrize(
    "fans_number, warning, expected_speed",
    (
        (2, [], 3),
        (1, [mock.call("Only 1 fan(s) available.", stacklevel=2)], 0),
    ),
)
def test_get_fan_speed(fans_number, warning, expected_speed, respx_mock: Router):
    fan_id = 2
    speed = 3
    json_response = {
        "status": {"fans": {f"fan_{fan_id}_speed": speed}},
        "nvm": {"installer_parameters": {"fans_number": fans_number}},
    }
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    with patch_warn() as m_warn:
        assert api.get_fan_speed(token, mac_address, fan_id) == expected_speed
    assert route.called
    assert m_warn.call_args_list == warning


@pytest.mark.parametrize(
    "fans_number, warning, expected_return",
    (
        (2, [], "'Command executed successfully'"),
        (1, [mock.call("Only 1 fan(s) available.", stacklevel=2)], ""),
    ),
)
def test_set_fan_speed(fans_number, warning, expected_return, respx_mock: Router):
    fan_id = 2
    speed = 3
    get_json_response = {"nvm": {"installer_parameters": {"fans_number": fans_number}}}
    put_json_response = "'Command executed successfully'"
    get_route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=get_json_response)
    put_route = respx_mock.put(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
    ) % Response(status_code=200, json=put_json_response)
    with patch_warn() as m_warn:
        assert api.set_fan_speed(token, mac_address, fan_id, speed) == expected_return
    assert get_route.called
    assert m_warn.call_args_list == warning
    if warning:
        assert not put_route.called
    else:
        assert put_route.called


def test_get_airkare(respx_mock: Router):
    airkare_function = False
    json_response = {"status": {"flags": {"is_airkare_active": airkare_function}}}
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_airkare(token, mac_address) == airkare_function
    assert route.called


def test_set_airkare(respx_mock: Router):
    airkare = True
    json_response = "'Command executed successfully'"
    route = respx_mock.put(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
    ) % Response(status_code=200, json=json_response)
    assert api.set_airkare(token, mac_address, airkare) == json_response
    assert route.called


def test_get_relax_mode(respx_mock: Router):
    relax_mode = False
    json_response = {"status": {"flags": {"is_relax_active": relax_mode}}}
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_relax_mode(token, mac_address) == relax_mode
    assert route.called


def test_set_relax_mode(respx_mock: Router):
    relax_mode = True
    json_response = "'Command executed successfully'"
    route = respx_mock.put(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
    ) % Response(status_code=200, json=json_response)
    assert api.set_relax_mode(token, mac_address, relax_mode) == json_response
    assert route.called


def test_get_manual_power_level(respx_mock: Router):
    manual_power = 1
    json_response = {"nvm": {"user_parameters": {"manual_power": manual_power}}}
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_manual_power_level(token, mac_address) == manual_power
    assert route.called


def test_set_manual_power_level(respx_mock: Router):
    power_level = 3
    json_response = "'Command executed successfully'"
    route = respx_mock.put(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
    ) % Response(status_code=200, json=json_response)
    assert api.set_manual_power_level(token, mac_address, power_level) == json_response
    assert route.called


def test_get_standby_mode(respx_mock: Router):
    is_standby_active = False
    json_response = {
        "nvm": {"user_parameters": {"is_standby_active": is_standby_active}}
    }
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_standby_mode(token, mac_address) == is_standby_active
    assert route.called


@pytest.mark.parametrize(
    "is_auto, warning, expected_return",
    (
        (True, [], "'Command executed successfully'"),
        (
            False,
            [mock.call("Standby mode is only available from auto mode.", stacklevel=2)],
            "",
        ),
    ),
)
def test_set_standby_mode(is_auto, warning, expected_return, respx_mock: Router):
    standby_mode = True
    get_json_response = {"nvm": {"user_parameters": {"is_auto": is_auto}}}
    put_json_response = "'Command executed successfully'"
    get_route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=get_json_response)
    put_route = respx_mock.put(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
    ) % Response(status_code=200, json=put_json_response)
    with patch_warn() as m_warn:
        assert api.set_standby_mode(token, mac_address, standby_mode) == expected_return
    assert get_route.called
    assert m_warn.call_args_list == warning
    if warning:
        assert not put_route.called
    else:
        assert put_route.called


def test_get_chrono_mode(respx_mock: Router):
    mode = False
    json_response = {"status": {"flags": {"is_crono_active": mode}}}
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_chrono_mode(token, mac_address) == mode
    assert route.called


def test_set_chrono_mode(respx_mock: Router):
    mode = True
    json_response = "'Command executed successfully'"
    route = respx_mock.put(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
    ) % Response(status_code=200, json=json_response)
    assert api.set_chrono_mode(token, mac_address, mode) == json_response
    assert route.called


@pytest.mark.parametrize(
    "mode, time, expected_return",
    (
        (False, 1234, 0),
        (True, 1234, 1234),
    ),
)
def test_get_easy_timer(mode, time, expected_return, respx_mock: Router):
    json_response = {
        "status": {"flags": {"is_easytimer_active": mode}, "easytimer": {"time": time}}
    }
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_easy_timer(token, mac_address) == expected_return
    assert route.called


def test_set_easy_timer(respx_mock: Router):
    mode = True
    json_response = "'Command executed successfully'"
    route = respx_mock.put(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/mqtt/command"
    ) % Response(status_code=200, json=json_response)
    assert api.set_easy_timer(token, mac_address, mode) == json_response
    assert route.called


def test_get_autonomy_time(respx_mock: Router):
    time = 2100
    json_response = {"status": {"pellet": {"autonomy_time": time}}}
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_autonomy_time(token, mac_address) == time
    assert route.called


def test_get_pellet_reserve(respx_mock: Router):
    mode = False
    json_response = {"status": {"flags": {"is_pellet_in_reserve": mode}}}
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_pellet_reserve(token, mac_address) == mode
    assert route.called


def test_device_info_get_serial_number():
    serial = "ABC123456"
    info = {"component_info": {"motherboard": {"serial_number": serial}}}
    assert api.device_info_get_serial_number(info) == serial


def test_get_serial_number(respx_mock: Router):
    serial = "ABC123456"
    json_response = {"component_info": {"motherboard": {"serial_number": serial}}}
    route = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/aabbccddeeff/info"
    ) % Response(status_code=200, json=json_response)
    assert api.get_serial_number(token, mac_address) == serial
    assert route.called
