import asyncio

import pytest

from omx_remote.execution.async_boundary import run_blocking_call


def test_run_blocking_call_preserves_return_value() -> None:
    def combine(prefix: str, value: int) -> str:
        return f"{prefix}-{value}"

    result = asyncio.run(run_blocking_call(combine, "item", 3))

    assert result == "item-3"


def test_run_blocking_call_forwards_keyword_arguments() -> None:
    def combine(*, prefix: str, value: int) -> str:
        return f"{prefix}-{value}"

    result = asyncio.run(run_blocking_call(combine, prefix="item", value=3))

    assert result == "item-3"


def test_run_blocking_call_propagates_exceptions() -> None:
    def fail() -> str:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(run_blocking_call(fail))
