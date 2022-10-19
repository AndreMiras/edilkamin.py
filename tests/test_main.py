from unittest import mock

from test_api import patch_cognito, patch_requests_get, patch_requests_put

from edilkamin import __main__


def test_main():
    access_token = "token"
    env = {
        "USERNAME": "username",
        "PASSWORD": "password",
        "MAC_ADDRESS": "mac_address",
    }
    with mock.patch.dict("os.environ", env), patch_cognito(
        access_token
    ) as m_cognito, patch_requests_get() as m_get, patch_requests_put() as m_put:
        assert __main__.main() is None
    assert m_cognito.called is True
    assert m_get.called is True
    assert m_put.called is True
