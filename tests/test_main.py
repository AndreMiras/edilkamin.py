from unittest import mock

import pytest
from test_api import patch_cognito, patch_httpx_get, patch_httpx_put

from edilkamin import __main__


def patch_discover_devices():
    return mock.patch("edilkamin.__main__.discover_devices")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "env, discover_devices_called",
    (
        ({}, True),
        ({"MAC_ADDRESS": "mac_address"}, False),
    ),
)
async def test_main(env, discover_devices_called):
    access_token = "token"
    env = {
        **{
            "USERNAME": "username",
            "PASSWORD": "password",
        },
        **env,
    }
    with mock.patch.dict("os.environ", env), patch_cognito(access_token) as m_cognito:
        with patch_httpx_get({}) as m_get, patch_httpx_put({}) as m_put:
            with patch_discover_devices() as m_discover_devices:
                assert await __main__.main() is None
    assert m_cognito.called is True
    assert m_get.called is True
    assert m_put.called is True
    assert m_discover_devices.called is discover_devices_called
