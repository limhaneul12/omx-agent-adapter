import asyncio

from omx_remote.schemas.invoke_command_schemas import OmxCommandResult
from omx_remote.schemas.teamwork.api_snapshot_schemas import TeamApiWorkerStatusSnapshot
from omx_remote.schemas.teamwork.operator_schemas import (
    TeamOperatorDispatchInstructionRequest,
    TeamOperatorDispatchTaskRequest,
    TeamOperatorTaskApprovalRequest,
    TeamOperatorWorkerRecheckRequest,
)
from omx_remote.teamwork import team_operator_facade


def test_dispatch_team_instruction_uses_direct_message_for_non_durable_worker_target(
    monkeypatch,
) -> None:
    async def fake_send_team_message(request):
        assert request.to_worker == "worker-1"
        return OmxCommandResult(exit_code=0, stdout="{}", stderr="")

    monkeypatch.setattr(
        team_operator_facade, "send_team_message", fake_send_team_message
    )

    result = asyncio.run(
        team_operator_facade.dispatch_team_instruction(
            TeamOperatorDispatchInstructionRequest(
                team_name="alpha",
                from_worker="leader-fixed",
                to_worker="worker-1",
                body="Please re-run checks.",
            )
        )
    )

    assert result.selected_operation == "send-message"
    assert result.outcome == "accepted"
    assert result.needs_follow_up is False


def test_dispatch_team_instruction_uses_worker_inbox_for_durable_target(
    monkeypatch,
) -> None:
    async def fake_write_team_worker_inbox(request):
        assert request.worker == "worker-1"
        return OmxCommandResult(exit_code=0, stdout="{}", stderr="")

    monkeypatch.setattr(
        team_operator_facade,
        "write_team_worker_inbox",
        fake_write_team_worker_inbox,
    )

    result = asyncio.run(
        team_operator_facade.dispatch_team_instruction(
            TeamOperatorDispatchInstructionRequest(
                team_name="alpha",
                from_worker="leader-fixed",
                to_worker="worker-1",
                body="Please re-run checks.",
                durable_delivery=True,
            )
        )
    )

    assert result.selected_operation == "write-worker-inbox"
    assert result.outcome == "accepted_but_unverified"
    assert result.needs_follow_up is True


def test_dispatch_team_instruction_uses_broadcast_without_worker_target(
    monkeypatch,
) -> None:
    async def fake_broadcast_team_message(request):
        assert request.from_worker == "leader-fixed"
        return OmxCommandResult(exit_code=0, stdout="{}", stderr="")

    monkeypatch.setattr(
        team_operator_facade,
        "broadcast_team_message",
        fake_broadcast_team_message,
    )

    result = asyncio.run(
        team_operator_facade.dispatch_team_instruction(
            TeamOperatorDispatchInstructionRequest(
                team_name="alpha",
                from_worker="leader-fixed",
                body="Heads up.",
            )
        )
    )

    assert result.selected_operation == "broadcast"
    assert result.outcome == "accepted"


def test_dispatch_team_instruction_reports_failure_for_non_zero_exit(
    monkeypatch,
) -> None:
    async def fake_send_team_message(request):
        _ = request
        return OmxCommandResult(exit_code=1, stdout="{}", stderr="team_not_found")

    monkeypatch.setattr(
        team_operator_facade, "send_team_message", fake_send_team_message
    )

    result = asyncio.run(
        team_operator_facade.dispatch_team_instruction(
            TeamOperatorDispatchInstructionRequest(
                team_name="alpha",
                from_worker="leader-fixed",
                to_worker="worker-1",
                body="Please re-run checks.",
            )
        )
    )

    assert result.outcome == "failed"
    assert result.needs_follow_up is True


def test_dispatch_team_task_wraps_create_task_result(monkeypatch) -> None:
    async def fake_create_team_task(request):
        assert request.subject == "Ship slice"
        return OmxCommandResult(exit_code=0, stdout="{}", stderr="")

    monkeypatch.setattr(team_operator_facade, "create_team_task", fake_create_team_task)

    result = asyncio.run(
        team_operator_facade.dispatch_team_task(
            TeamOperatorDispatchTaskRequest(
                team_name="alpha",
                subject="Ship slice",
                description="Finish the next operator step.",
            )
        )
    )

    assert result.selected_operation == "create-task"
    assert result.outcome == "accepted_but_unverified"
    assert result.needs_follow_up is True


def test_request_task_approval_marks_success_like_result_as_unverified(
    monkeypatch,
) -> None:
    async def fake_write_team_task_approval(request):
        assert request.status == "approved"
        return OmxCommandResult(exit_code=0, stdout="{}", stderr="")

    monkeypatch.setattr(
        team_operator_facade,
        "write_team_task_approval",
        fake_write_team_task_approval,
    )

    result = asyncio.run(
        team_operator_facade.request_task_approval(
            TeamOperatorTaskApprovalRequest(
                team_name="alpha",
                task_id="1",
                status="approved",
                reviewer="leader-fixed",
                decision_reason="looks good",
            )
        )
    )

    assert result.selected_operation == "write-task-approval"
    assert result.outcome == "accepted_but_unverified"
    assert result.needs_follow_up is True


def test_request_worker_recheck_uses_durable_inbox_for_unknown_worker_state(
    monkeypatch,
) -> None:
    async def fake_read_worker_status(request):
        assert request.worker == "worker-1"
        return TeamApiWorkerStatusSnapshot(
            worker="worker-1",
            state="unknown",
            updated_at="1970-01-01T00:00:00.000Z",
        )

    async def fake_dispatch_team_instruction(request):
        assert request.durable_delivery is True
        return team_operator_facade.TeamOperatorDispatchOutcome(
            selected_operation="write-worker-inbox",
            outcome="accepted_but_unverified",
            needs_follow_up=True,
            reason="worker state unknown so durable inbox chosen",
            command_result=OmxCommandResult(exit_code=0, stdout="{}", stderr=""),
        )

    monkeypatch.setattr(
        team_operator_facade,
        "read_team_api_read_worker_status",
        fake_read_worker_status,
    )
    monkeypatch.setattr(
        team_operator_facade,
        "dispatch_team_instruction",
        fake_dispatch_team_instruction,
    )

    result = asyncio.run(
        team_operator_facade.request_worker_recheck(
            TeamOperatorWorkerRecheckRequest(
                team_name="alpha",
                from_worker="leader-fixed",
                worker="worker-1",
                body="Please re-run checks.",
            )
        )
    )

    assert result.worker_state == "unknown"
    assert result.selected_delivery_mode == "durable_inbox"
    assert result.dispatch_result.selected_operation == "write-worker-inbox"


def test_request_worker_recheck_uses_direct_message_for_reporting_worker(
    monkeypatch,
) -> None:
    async def fake_read_worker_status(request):
        assert request.worker == "worker-1"
        return TeamApiWorkerStatusSnapshot(
            worker="worker-1",
            state="idle",
            updated_at="1970-01-01T00:00:00.000Z",
        )

    async def fake_dispatch_team_instruction(request):
        assert request.durable_delivery is False
        return team_operator_facade.TeamOperatorDispatchOutcome(
            selected_operation="send-message",
            outcome="accepted",
            needs_follow_up=False,
            reason="worker state is reporting so direct message chosen",
            command_result=OmxCommandResult(exit_code=0, stdout="{}", stderr=""),
        )

    monkeypatch.setattr(
        team_operator_facade,
        "read_team_api_read_worker_status",
        fake_read_worker_status,
    )
    monkeypatch.setattr(
        team_operator_facade,
        "dispatch_team_instruction",
        fake_dispatch_team_instruction,
    )

    result = asyncio.run(
        team_operator_facade.request_worker_recheck(
            TeamOperatorWorkerRecheckRequest(
                team_name="alpha",
                from_worker="leader-fixed",
                worker="worker-1",
                body="Please re-run checks.",
            )
        )
    )

    assert result.worker_state == "idle"
    assert result.selected_delivery_mode == "direct_message"
    assert result.dispatch_result.selected_operation == "send-message"
