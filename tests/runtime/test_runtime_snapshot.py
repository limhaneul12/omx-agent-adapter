import asyncio
import inspect

from omx_remote.runtime import runtime_snapshot
from omx_remote.schemas.runtime import RuntimeStatusRequest


class DummyResult:
    def __init__(self, stdout: str = "ok", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_runtime_status_uses_stdout(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_snapshot,
        "run_omx_command",
        lambda args: DummyResult(stdout="No active modes.\n"),
    )

    result = asyncio.run(runtime_snapshot.read_runtime_status())

    assert result.summary == "No active modes."
    assert result.has_active_modes is False
    assert result.active_mode_names == []
    assert result.mode_statuses == {}


def test_read_runtime_status_accepts_typed_request(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_snapshot,
        "run_omx_command",
        lambda args: DummyResult(stdout="No active modes.\n"),
    )

    result = asyncio.run(
        runtime_snapshot.read_runtime_status(RuntimeStatusRequest())
    )

    assert result.summary == "No active modes."
    assert result.has_active_modes is False


def test_read_runtime_status_falls_back_to_stderr(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_snapshot,
        "run_omx_command",
        lambda args: DummyResult(stdout="", stderr="worker notify failed\n"),
    )

    result = asyncio.run(runtime_snapshot.read_runtime_status())

    assert result.summary == "worker notify failed"
    assert result.has_active_modes is None
    assert result.active_mode_names == []
    assert result.mode_statuses == {}
    assert len(result.anomalies) == 1
    assert result.anomalies[0].category == "stderr_fallback"
    assert result.anomalies[0].message == "worker notify failed"


def test_read_runtime_status_marks_active_modes_when_summary_is_not_idle(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_snapshot,
        "run_omx_command",
        lambda args: DummyResult(stdout="ralph: active\n"),
    )

    result = asyncio.run(runtime_snapshot.read_runtime_status())

    assert result.summary == "ralph: active"
    assert result.has_active_modes is True
    assert result.active_mode_names == ["ralph"]
    assert result.mode_statuses == {"ralph": "active"}
    assert [mode_snapshot.name for mode_snapshot in result.mode_snapshots] == ["ralph"]
    assert result.mode_snapshots[0].status == "active"
    assert result.anomalies == []


def test_read_runtime_status_extracts_multiple_active_mode_names(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_snapshot,
        "run_omx_command",
        lambda args: DummyResult(stdout="ralph: active\nteam: active\n"),
    )

    result = asyncio.run(runtime_snapshot.read_runtime_status())

    assert result.summary == "ralph: active\nteam: active"
    assert result.has_active_modes is True
    assert result.active_mode_names == ["ralph", "team"]
    assert result.mode_statuses == {"ralph": "active", "team": "active"}


def test_read_runtime_status_builds_per_mode_snapshots_for_mixed_statuses(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_snapshot,
        "run_omx_command",
        lambda args: DummyResult(stdout="ralph: active\nteam: paused\nhud: idle\n"),
    )

    result = asyncio.run(runtime_snapshot.read_runtime_status())

    assert [mode_snapshot.name for mode_snapshot in result.mode_snapshots] == [
        "ralph",
        "team",
        "hud",
    ]
    assert [mode_snapshot.status for mode_snapshot in result.mode_snapshots] == [
        "active",
        "paused",
        "idle",
    ]
    assert [mode_snapshot.raw_status_text for mode_snapshot in result.mode_snapshots] == [
        "active",
        "paused",
        "idle",
    ]
    assert [mode_snapshot.has_uncertainty for mode_snapshot in result.mode_snapshots] == [
        False,
        False,
        False,
    ]


def test_read_runtime_status_parses_inactive_phase_lines_without_unknown_anomalies(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_snapshot,
        "run_omx_command",
        lambda args: DummyResult(
            stdout="hud: inactive (phase: n/a)\nralph: ACTIVE (phase: starting)\nteam: inactive (phase: cancelled)\n"
        ),
    )

    result = asyncio.run(runtime_snapshot.read_runtime_status())

    assert result.has_active_modes is True
    assert result.active_mode_names == ["ralph"]
    assert result.mode_statuses == {
        "hud": "idle",
        "ralph": "active",
        "team": "idle",
    }
    assert [mode_snapshot.status for mode_snapshot in result.mode_snapshots] == [
        "idle",
        "active",
        "idle",
    ]
    assert [mode_snapshot.raw_status_text for mode_snapshot in result.mode_snapshots] == [
        "inactive (phase: n/a)",
        "ACTIVE (phase: starting)",
        "inactive (phase: cancelled)",
    ]
    assert result.anomalies == []


def test_read_runtime_status_surfaces_unknown_status_anomalies(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_snapshot,
        "run_omx_command",
        lambda args: DummyResult(stdout="ralph: active\nteam: spinning\n"),
    )

    result = asyncio.run(runtime_snapshot.read_runtime_status())

    assert result.mode_statuses == {"ralph": "active", "team": "unknown"}
    assert len(result.anomalies) == 1
    assert result.anomalies[0].category == "unknown_mode_status"
    assert result.anomalies[0].mode_name == "team"
    assert result.anomalies[0].message == "spinning"
    assert result.has_anomalies is True
    assert result.anomaly_count == 1
    assert result.mode_snapshots[1].name == "team"
    assert result.mode_snapshots[1].status == "unknown"
    assert result.mode_snapshots[1].raw_status_text == "spinning"
    assert result.mode_snapshots[1].has_uncertainty is True


def test_read_runtime_status_reports_empty_transport_output(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_snapshot,
        "run_omx_command",
        lambda args: DummyResult(stdout="", stderr=""),
    )

    result = asyncio.run(runtime_snapshot.read_runtime_status())

    assert result.summary == ""
    assert result.has_active_modes is None
    assert result.mode_statuses == {}
    assert len(result.anomalies) == 1
    assert result.anomalies[0].category == "empty_transport_output"
    assert result.anomalies[0].message == "omx status returned no stdout or stderr output"
    assert result.anomalies[0].mode_name is None


def test_read_runtime_status_keeps_stderr_fallback_when_stdout_has_noise_lines(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        runtime_snapshot,
        "run_omx_command",
        lambda args: DummyResult(stdout="status ok\n", stderr="worker notify failed\n"),
    )

    result = asyncio.run(runtime_snapshot.read_runtime_status())

    assert result.summary == "status ok"
    assert result.has_active_modes is True
    assert result.mode_statuses == {}
    assert len(result.anomalies) == 1
    assert result.anomalies[0].category == "unparseable_stdout"
    assert result.anomalies[0].message == "status ok"
    assert result.anomalies[0].mode_name is None


def test_read_runtime_status_reports_no_anomalies_for_idle_stdout(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_snapshot,
        "run_omx_command",
        lambda args: DummyResult(stdout="No active modes.\n", stderr=""),
    )

    result = asyncio.run(runtime_snapshot.read_runtime_status())

    assert result.anomalies == []
    assert result.has_anomalies is False
    assert result.anomaly_count == 0




def test_extract_active_mode_names_ignores_non_status_lines() -> None:
    stdout = "ralph: active\nstatus ok\nteam: active\n"

    result = runtime_snapshot._extract_active_mode_names(stdout)

    assert result == ["ralph", "team"]


def test_parse_active_mode_name_rejects_non_active_status() -> None:
    assert runtime_snapshot._parse_active_mode_name("team: paused") is None


def test_extract_mode_statuses_keeps_known_non_active_status_tokens() -> None:
    stdout = "ralph: active\nteam: paused\nhud: idle\n"

    result = runtime_snapshot._extract_mode_statuses(stdout)

    assert result == {"ralph": "active", "team": "paused", "hud": "idle"}


def test_extract_mode_statuses_preserves_unknown_status_tokens() -> None:
    stdout = "ralph: active\nteam: spinning\n"

    result = runtime_snapshot._extract_mode_statuses(stdout)

    assert result == {"ralph": "active", "team": "unknown"}


def test_read_runtime_status_is_async() -> None:
    assert inspect.iscoroutinefunction(runtime_snapshot.read_runtime_status)
