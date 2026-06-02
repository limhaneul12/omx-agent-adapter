from __future__ import annotations

import orjson

from omx_remote.runtime.company_run import company_run_team_evidence
from omx_remote.schemas.invoke_command_schemas import OmxCommandResult


def test_team_completion_evidence_reads_native_status_counts(monkeypatch) -> None:
    payload = {
        "team_name": "company-run-test",
        "status": "ok",
        "phase": "complete",
        "tasks": {
            "total": 12,
            "pending": 0,
            "blocked": 0,
            "in_progress": 0,
            "completed": 12,
            "failed": 0,
        },
        "workers": {
            "total": 4,
            "dead": 0,
            "non_reporting": 0,
        },
    }

    def fake_run_omx_command(*, arguments, cwd):
        assert arguments == ("team", "status", "company-run-test", "--json")
        assert cwd
        return OmxCommandResult(
            exit_code=0,
            stdout=orjson.dumps(payload).decode(),
            stderr="",
        )

    monkeypatch.setattr(
        company_run_team_evidence,
        "run_omx_command",
        fake_run_omx_command,
    )

    evidence = company_run_team_evidence.team_state_completion_evidence(
        cwd=company_run_team_evidence.Path.cwd(),
        team_name="company-run-test",
    )

    assert evidence.complete is True
    assert evidence.task_count == 12
    assert evidence.completed_count == 12
    assert evidence.blocked_count == 0
    assert evidence.incomplete_count == 0
    assert evidence.blocked_worker_count == 0
    assert evidence.terminal is False


def test_team_completion_evidence_treats_missing_team_as_terminal(monkeypatch) -> None:
    payload = {
        "team_name": "company-run-test",
        "status": "missing",
    }

    def fake_run_omx_command(*, arguments, cwd):
        assert arguments == ("team", "status", "company-run-test", "--json")
        assert cwd
        return OmxCommandResult(
            exit_code=0,
            stdout=orjson.dumps(payload).decode(),
            stderr="",
        )

    monkeypatch.setattr(
        company_run_team_evidence,
        "run_omx_command",
        fake_run_omx_command,
    )

    evidence = company_run_team_evidence.wait_for_team_completion_evidence(
        cwd=company_run_team_evidence.Path.cwd(),
        team_name="company-run-test",
        timeout_seconds=60.0,
    )

    assert evidence.complete is False
    assert evidence.terminal is True
    assert "missing" in evidence.detail
