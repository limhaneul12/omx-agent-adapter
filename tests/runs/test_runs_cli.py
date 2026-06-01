from pathlib import Path

import orjson
from typer.testing import CliRunner

from omx_remote.cli import app


def _record_review_run(tmp_path: Path) -> str:
    result = CliRunner().invoke(
        app,
        [
            "run",
            "builtin:review-gate",
            "--cwd",
            str(tmp_path),
            "--dry-run",
            "--record-run",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    run_id: str = payload["run_record"]["run_id"]
    return run_id


def test_run_record_flag_writes_run_artifacts(tmp_path: Path) -> None:
    run_id = _record_review_run(tmp_path)
    run_dir = tmp_path / ".comx-agent" / "runs" / run_id

    assert (run_dir / "run.json").exists()
    assert (run_dir / "plan.json").exists()
    assert (run_dir / "handoff.md").exists()


def test_runs_cli_lists_shows_handoff_and_replay_plan(tmp_path: Path) -> None:
    run_id = _record_review_run(tmp_path)

    list_result = CliRunner().invoke(
        app,
        ["runs", "list", "--cwd", str(tmp_path), "--json"],
    )
    show_result = CliRunner().invoke(
        app,
        ["runs", "show", run_id, "--cwd", str(tmp_path), "--json"],
    )
    handoff_result = CliRunner().invoke(
        app,
        ["runs", "handoff", run_id, "--cwd", str(tmp_path)],
    )
    replay_result = CliRunner().invoke(
        app,
        ["runs", "replay-plan", run_id, "--cwd", str(tmp_path), "--dry-run", "--json"],
    )

    assert list_result.exit_code == 0
    assert show_result.exit_code == 0
    assert handoff_result.exit_code == 0
    assert replay_result.exit_code == 0

    list_payload = orjson.loads(list_result.stdout)
    show_payload = orjson.loads(show_result.stdout)
    replay_payload = orjson.loads(replay_result.stdout)

    assert list_payload["records"][0]["run_id"] == run_id
    assert show_payload["run_id"] == run_id
    assert f"Run {run_id}" in handoff_result.stdout
    assert replay_payload["run_id"] == run_id
    assert replay_payload["plan"]["qualified_id"] == "builtin:review-gate"


def test_runs_list_json_reports_corrupted_record_without_traceback(
    tmp_path: Path,
) -> None:
    corrupt_run_dir = tmp_path / ".comx-agent" / "runs" / "9999-corrupt"
    corrupt_run_dir.mkdir(parents=True)
    (corrupt_run_dir / "run.json").write_text("{not-json", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        ["runs", "list", "--cwd", str(tmp_path), "--json"],
    )

    assert result.exit_code == 2
    payload = orjson.loads(result.stdout)
    assert payload["ok"] is False
    assert "error" in payload
    assert "Traceback" not in result.stdout
    assert "Traceback" not in (result.stderr or "")
