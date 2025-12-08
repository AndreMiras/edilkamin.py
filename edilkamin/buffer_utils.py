"""Utilities for handling gzip-compressed Buffer responses from the API."""

import gzip
import json
import typing
import warnings


def is_buffer(value: typing.Any) -> bool:
    """Check if a value is a Node.js Buffer object.

    Node.js Buffer format: {"type": "Buffer", "data": [int, int, ...]}

    Args:
        value: Any value to check

    Returns:
        True if value is a Buffer object, False otherwise

    Examples:
        >>> is_buffer({"type": "Buffer", "data": [31, 139, 8, 0]})
        True
        >>> is_buffer({"type": "String", "data": []})
        False
        >>> is_buffer({"mac_address": "abc123"})
        False
        >>> is_buffer("plain string")
        False
    """
    if not isinstance(value, dict):
        return False
    return value.get("type") == "Buffer" and "data" in value


def decompress_buffer(buffer_obj: typing.Dict) -> typing.Any:
    """Decompress a Node.js Buffer containing gzip data.

    Args:
        buffer_obj: Buffer object with format {"type": "Buffer", "data": [bytes]}

    Returns:
        Decompressed and JSON-parsed data, or original buffer_obj if decompression fails

    Examples:
        >>> # Example with actual gzip data
        >>> # see tests/test_buffer_utils.py for executable tests
        >>> buffer = {"type": "Buffer", "data": [31, 139, 8, 0, ...]}  # doctest: +SKIP
        >>> result = decompress_buffer(buffer)  # doctest: +SKIP
        >>> isinstance(result, dict)  # doctest: +SKIP
        True
    """
    if not is_buffer(buffer_obj):
        return buffer_obj

    try:
        # Convert list of ints to bytes
        compressed_bytes = bytes(buffer_obj["data"])

        # Decompress gzip data
        decompressed = gzip.decompress(compressed_bytes)

        # Parse as JSON
        return json.loads(decompressed)
    except (
        KeyError,
        ValueError,
        TypeError,
        gzip.BadGzipFile,
        json.JSONDecodeError,
    ) as e:
        # If decompression fails, return original value
        # This maintains backward compatibility if API changes format again
        warnings.warn(
            f"Failed to decompress buffer: {e}. Returning original value.",
            stacklevel=2,
        )
        return buffer_obj


def process_response(response: typing.Dict) -> typing.Dict:
    """Recursively process API response, decompressing any Buffer fields.

    Args:
        response: API response dictionary that may contain Buffer objects

    Returns:
        Response with all Buffer objects decompressed

    Examples:
        >>> # See tests/test_buffer_utils.py for executable tests
        >>> response = {  # doctest: +SKIP
        ...     "component_info": {"type": "Buffer", "data": [...]},
        ...     "mac_address": "abc123",
        ...     "nested": {"inner": {"type": "Buffer", "data": [...]}}
        ... }
        >>> result = process_response(response)  # doctest: +SKIP
    """
    if not isinstance(response, dict):
        return response

    result = {}
    for key, value in response.items():
        if is_buffer(value):
            # Decompress buffer
            result[key] = decompress_buffer(value)
        elif isinstance(value, dict):
            # Recursively process nested dicts
            result[key] = process_response(value)
        elif isinstance(value, list):
            # Process lists (in case buffers appear in arrays)
            result[key] = [
                decompress_buffer(item)
                if is_buffer(item)
                else process_response(item)
                if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            # Keep plain values as-is
            result[key] = value

    return result
