import asyncio

import pytest
from pydantic import ValidationError

from omx_remote.execution.event_feed import decode_event_lines
from omx_remote.schemas.execution_schemas import ExecRequest


def test_exec_request_rejects_empty_prompt() -> None:
    with pytest.raises(ValidationError):
        ExecRequest.model_validate({"prompt": ""})


def test_decode_event_lines_rejects_empty_raw_payload_via_request_boundary() -> None:
    with pytest.raises(ValidationError):
        asyncio.run(decode_event_lines(""))
