import math

import pytest

from omx_remote.runtime.mcp.mcp_json_payloads import (
    normalize_mcp_json_object,
    normalize_mcp_json_object_list,
)


def test_normalize_mcp_json_object_rejects_non_finite_float() -> None:
    with pytest.raises(ValueError, match="invalid MCP payload"):
        normalize_mcp_json_object({"value": math.nan}, "invalid MCP payload")


def test_normalize_mcp_json_object_list_rejects_non_finite_float() -> None:
    with pytest.raises(ValueError, match="invalid MCP payload"):
        normalize_mcp_json_object_list(
            [{"value": math.inf}],
            "invalid MCP payload",
        )
