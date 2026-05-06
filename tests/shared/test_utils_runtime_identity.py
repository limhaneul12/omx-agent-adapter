from datetime import datetime
from pathlib import Path

import pytest

from omx_remote.shared.utils.runtime_identity import build_scoped_id, utcnow_text


def test_utcnow_text_returns_utc_isoformat_text() -> None:
    timestamp_text: str = utcnow_text()

    parsed_timestamp = datetime.fromisoformat(timestamp_text)

    assert parsed_timestamp.tzinfo is not None
    assert parsed_timestamp.utcoffset().total_seconds() == 0


def test_build_scoped_id_uses_target_prefix() -> None:
    result: str = build_scoped_id("goal")

    assert result.startswith("goal-")
    assert len(result) == len("goal-") + 12


def test_build_scoped_id_rejects_blank_target() -> None:
    with pytest.raises(ValueError, match="target must not be blank"):
        build_scoped_id("   ")


def test_runtime_identity_helpers_are_not_split_into_one_function_modules() -> None:
    assert not Path("src/omx_remote/shared/utils/identifiers.py").exists()
    assert not Path("src/omx_remote/shared/utils/time_text.py").exists()
