from __future__ import annotations

import orjson

from omx_remote.runtime.company_run import company_run_team_evidence
from omx_remote.schemas.invoke_command_schemas import OmxCommandResult


def test_team_completion_evidence_reads_native_status_counts(monkeypatch) -> None:
    status_payload = {
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
    task_list_payload = {
        "ok": True,
        "data": {
            "count": 12,
            "tasks": tuple(
                {
                    "id": str(task_id),
                    "status": "completed",
                    "owner": f"worker-{((task_id - 1) % 4) + 1}",
                }
                for task_id in range(1, 13)
            ),
        },
    }

    def fake_run_omx_command(*, arguments, cwd):
        assert cwd
        if arguments == ("team", "status", "company-run-test", "--json"):
            payload = status_payload
        else:
            assert arguments[:4] == ("team", "api", "list-tasks", "--input")
            assert arguments[5:] == ("--json",)
            assert orjson.loads(arguments[4]) == {"team_name": "company-run-test"}
            payload = task_list_payload
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


def test_team_completion_evidence_rejects_single_worker_owner_distribution(
    monkeypatch,
) -> None:
    status_payload = {
        "team_name": "company-run-test",
        "status": "ok",
        "phase": "complete",
        "tasks": {
            "total": 4,
            "pending": 0,
            "blocked": 0,
            "in_progress": 0,
            "completed": 4,
            "failed": 0,
        },
        "workers": {
            "total": 4,
            "dead": 0,
            "non_reporting": 0,
        },
    }
    task_list_payload = {
        "ok": True,
        "data": {
            "count": 4,
            "tasks": tuple(
                {
                    "id": str(task_id),
                    "status": "completed",
                    "owner": "worker-1",
                }
                for task_id in range(1, 5)
            ),
        },
    }

    def fake_run_omx_command(*, arguments, cwd):
        assert cwd
        if arguments == ("team", "status", "company-run-test", "--json"):
            payload = status_payload
        else:
            assert arguments[:4] == ("team", "api", "list-tasks", "--input")
            assert arguments[5:] == ("--json",)
            assert orjson.loads(arguments[4]) == {"team_name": "company-run-test"}
            payload = task_list_payload
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

    assert evidence.complete is False
    assert evidence.completed_count == 4
    assert "1 distinct owners" in evidence.detail
    assert "Owner distribution is invalid" in evidence.detail


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
