from pathlib import Path

from omx_remote.runtime.preflight.prompt_file_preflight import check_prompt_file
from omx_remote.schemas.preflight.preflight_schemas import PreflightSeverity


def test_existing_prompt_file_inside_cwd_passes(tmp_path: Path) -> None:
    prompt_path = tmp_path / "prompts" / "task.md"
    prompt_path.parent.mkdir()
    prompt_path.write_text("Do the task.")

    result = check_prompt_file(tmp_path, Path("prompts/task.md"))

    assert result.severity == PreflightSeverity.INFO
    assert result.blocks_execution is False
    assert str(prompt_path) in result.evidence


def test_missing_prompt_file_blocks(tmp_path: Path) -> None:
    result = check_prompt_file(tmp_path, Path("prompts/missing.md"))

    assert result.severity == PreflightSeverity.BLOCKER
    assert result.blocks_execution is True
    assert "does not exist" in result.summary


def test_prompt_file_outside_cwd_blocks(tmp_path: Path) -> None:
    outside_path = tmp_path.parent / "outside-task.md"
    outside_path.write_text("Outside prompt.")

    result = check_prompt_file(tmp_path, outside_path)

    assert result.severity == PreflightSeverity.BLOCKER
    assert result.blocks_execution is True
    assert "outside" in result.summary
