from unittest import mock

import pytest
from httpx import Response
from respx import Router
from test_api import DEVICE_INFO_URL, MQTT_COMMAND_URL, patch_cognito

from edilkamin import __main__


def patch_discover_devices():
    m = mock.Mock(return_value=["aabbccddeeff"])
    return mock.patch("edilkamin.__main__.discover_devices", m)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "env, discover_devices_called",
    (
        ({}, True),
        ({"MAC_ADDRESS": "mac_address"}, False),
    ),
)
async def test_main(env, discover_devices_called, respx_mock: Router):
    access_token = "token"
    env = {
        **{
            "USERNAME": "username",
            "PASSWORD": "password",
        },
        **env,
    }
    # Mock HTTP endpoints for both possible MAC values used in the test
    get_route_discovered = respx_mock.get(DEVICE_INFO_URL) % Response(
        status_code=200, json={}
    )
    get_route_env = respx_mock.get(
        "https://fxtj7xkgc6.execute-api.eu-central-1.amazonaws.com/prod/device/mac_address/info"
    ) % Response(status_code=200, json={})
    put_route = respx_mock.put(MQTT_COMMAND_URL) % Response(status_code=200, json={})
    with mock.patch.dict("os.environ", env), patch_cognito(access_token) as m_cognito:
        with patch_discover_devices() as m_discover_devices:
            assert await __main__.main() is None
    assert m_cognito.called is True
    assert get_route_discovered.called or get_route_env.called
    assert put_route.called is True
    assert m_discover_devices.called is discover_devices_called
