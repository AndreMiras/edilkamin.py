import os

from edilkamin import constants


def get_endpoint(path: str, use_legacy_api: bool = False) -> str:
    """Construct full API endpoint URL.

    Args:
        path: API path (e.g., "device/aabbccddeeff/info")
        use_legacy_api: If True, use old AWS API URL

    Returns:
        Full URL to API endpoint
    """
    base_url = constants.OLD_API_URL if use_legacy_api else constants.NEW_API_URL
    return base_url + path


def get_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def assert_env(name: str) -> str:
    env = os.environ.get(name)
    assert env
    return env
