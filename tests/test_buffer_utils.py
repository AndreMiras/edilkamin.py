"""Tests for buffer decompression utilities."""

import gzip
import json

import pytest

from edilkamin import buffer_utils


class TestIsBuffer:
    """Tests for is_buffer() function."""

    def test_valid_buffer(self):
        """Valid Buffer object should be detected."""
        buffer_obj = {"type": "Buffer", "data": [1, 2, 3]}
        assert buffer_utils.is_buffer(buffer_obj) is True

    def test_wrong_type(self):
        """Object with wrong type should not be detected as Buffer."""
        obj = {"type": "String", "data": [1, 2, 3]}
        assert buffer_utils.is_buffer(obj) is False

    def test_missing_data(self):
        """Buffer without data field should not be valid."""
        obj = {"type": "Buffer"}
        assert buffer_utils.is_buffer(obj) is False

    def test_missing_type(self):
        """Object without type field should not be valid."""
        obj = {"data": [1, 2, 3]}
        assert buffer_utils.is_buffer(obj) is False

    def test_not_dict(self):
        """Non-dict values should return False."""
        assert buffer_utils.is_buffer("string") is False
        assert buffer_utils.is_buffer(123) is False
        assert buffer_utils.is_buffer([1, 2, 3]) is False
        assert buffer_utils.is_buffer(None) is False


class TestDecompressBuffer:
    """Tests for decompress_buffer() function."""

    def test_decompress_valid_gzip(self):
        """Should decompress valid gzip data and parse JSON."""
        # Create test data
        original_data = {"test": "value", "number": 42}
        json_bytes = json.dumps(original_data).encode("utf-8")
        compressed = gzip.compress(json_bytes)

        # Create Buffer object
        buffer_obj = {"type": "Buffer", "data": list(compressed)}

        # Decompress
        result = buffer_utils.decompress_buffer(buffer_obj)

        assert result == original_data

    def test_decompress_complex_nested_data(self):
        """Should handle complex nested JSON structures."""
        original_data = {
            "motherboard": {
                "serial_number": "ABC123",
                "version": "1.2.3",
                "nested": {"deep": {"value": 42}},
            },
            "array": [1, 2, 3],
            "boolean": True,
        }
        json_bytes = json.dumps(original_data).encode("utf-8")
        compressed = gzip.compress(json_bytes)
        buffer_obj = {"type": "Buffer", "data": list(compressed)}

        result = buffer_utils.decompress_buffer(buffer_obj)

        assert result == original_data

    def test_invalid_gzip_data_returns_original(self):
        """Should return original buffer if gzip decompression fails."""
        buffer_obj = {"type": "Buffer", "data": [1, 2, 3, 4, 5]}

        with pytest.warns(UserWarning, match="Failed to decompress buffer"):
            result = buffer_utils.decompress_buffer(buffer_obj)

        assert result == buffer_obj

    def test_invalid_json_returns_original(self):
        """Should return original if decompressed data is not valid JSON."""
        # Compress invalid JSON
        compressed = gzip.compress(b"not valid json {]")
        buffer_obj = {"type": "Buffer", "data": list(compressed)}

        with pytest.warns(UserWarning, match="Failed to decompress buffer"):
            result = buffer_utils.decompress_buffer(buffer_obj)

        assert result == buffer_obj

    def test_non_buffer_returns_unchanged(self):
        """Should return non-buffer values unchanged."""
        plain_value = {"some": "data"}
        result = buffer_utils.decompress_buffer(plain_value)
        assert result == plain_value


class TestProcessResponse:
    """Tests for process_response() function."""

    def test_process_simple_buffer_field(self):
        """Should decompress buffer field in response."""
        original = {"test": "data"}
        compressed = gzip.compress(json.dumps(original).encode())

        response = {
            "component_info": {"type": "Buffer", "data": list(compressed)},
            "mac_address": "abc123",
        }

        result = buffer_utils.process_response(response)

        assert result["component_info"] == original
        assert result["mac_address"] == "abc123"

    def test_process_multiple_buffer_fields(self):
        """Should decompress multiple buffer fields."""
        data1 = {"field1": "value1"}
        data2 = {"field2": "value2"}
        data3 = {"field3": "value3"}

        response = {
            "component_info": {
                "type": "Buffer",
                "data": list(gzip.compress(json.dumps(data1).encode())),
            },
            "nvm": {
                "type": "Buffer",
                "data": list(gzip.compress(json.dumps(data2).encode())),
            },
            "status": {
                "type": "Buffer",
                "data": list(gzip.compress(json.dumps(data3).encode())),
            },
            "pk": 1,
        }

        result = buffer_utils.process_response(response)

        assert result["component_info"] == data1
        assert result["nvm"] == data2
        assert result["status"] == data3
        assert result["pk"] == 1

    def test_process_nested_buffers(self):
        """Should recursively process nested buffers."""
        inner_data = {"nested": "value"}
        compressed = gzip.compress(json.dumps(inner_data).encode())

        response = {"outer": {"inner": {"type": "Buffer", "data": list(compressed)}}}

        result = buffer_utils.process_response(response)

        assert result["outer"]["inner"] == inner_data

    def test_process_buffers_in_arrays(self):
        """Should process buffers inside arrays."""
        data = {"item": "value"}
        compressed = gzip.compress(json.dumps(data).encode())

        response = {
            "items": [
                {"type": "Buffer", "data": list(compressed)},
                "plain_value",
                {"type": "Buffer", "data": list(compressed)},
            ]
        }

        result = buffer_utils.process_response(response)

        assert result["items"][0] == data
        assert result["items"][1] == "plain_value"
        assert result["items"][2] == data

    def test_process_plain_response_unchanged(self):
        """Should return plain JSON responses unchanged."""
        response = {
            "component_info": {"motherboard": {"serial": "ABC"}},
            "mac_address": "abc123",
            "nested": {"deep": {"value": 42}},
        }

        result = buffer_utils.process_response(response)

        assert result == response

    def test_process_empty_response(self):
        """Should handle empty responses."""
        result = buffer_utils.process_response({})
        assert result == {}

    def test_process_non_dict_returns_unchanged(self):
        """Should return non-dict values unchanged."""
        assert buffer_utils.process_response("string") == "string"
        assert buffer_utils.process_response(123) == 123
        assert buffer_utils.process_response(None) is None
