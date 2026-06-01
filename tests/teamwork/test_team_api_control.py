import asyncio
import inspect

from omx_remote.schemas.invoke_command_schemas import OmxCommandResult
from omx_remote.schemas.teamwork.api_request_schemas import (
    TeamApiBroadcastRequest,
    TeamApiClaimTaskRequest,
    TeamApiCleanupRequest,
    TeamApiCreateTaskRequest,
    TeamApiMailboxMarkDeliveredRequest,
    TeamApiMailboxMarkNotifiedRequest,
    TeamApiOrphanCleanupRequest,
    TeamApiReadShutdownAckRequest,
    TeamApiReadTaskApprovalRequest,
    TeamApiReadTaskRequest,
    TeamApiReleaseTaskClaimRequest,
    TeamApiSendMessageRequest,
    TeamApiTransitionTaskStatusRequest,
    TeamApiUpdateTaskRequest,
    TeamApiWorkerInboxWriteRequest,
    TeamApiWriteShutdownRequest,
    TeamApiWriteTaskApprovalRequest,
)
from omx_remote.teamwork import team_api_control


class DummyResult:
    def __init__(
        self, stdout: str = "{}", stderr: str = "", exit_code: int = 0
    ) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code


def test_send_team_message_is_async() -> None:
    assert inspect.iscoroutinefunction(team_api_control.send_team_message)


def test_send_team_message_accepts_typed_request() -> None:
    coroutine = team_api_control.send_team_message(
        TeamApiSendMessageRequest(
            team_name="alpha",
            from_worker="worker-1",
            to_worker="worker-2",
            body="ACK",
        )
    )

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)


def test_send_team_message_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=1, stdout="{}", stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.send_team_message(
            TeamApiSendMessageRequest(
                team_name="alpha",
                from_worker="worker-1",
                to_worker="worker-2",
                body="ACK",
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "send-message",
        "--input",
        '{"team_name":"alpha","from_worker":"worker-1","to_worker":"worker-2","body":"ACK"}',
        "--json",
    )
    assert result.exit_code == 1


def test_write_team_worker_inbox_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.write_team_worker_inbox(
            TeamApiWorkerInboxWriteRequest(
                team_name="alpha",
                worker="worker-1",
                content="# Inbox update\nProceed.",
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "write-worker-inbox",
        "--input",
        '{"team_name":"alpha","worker":"worker-1","content":"# Inbox update\\nProceed."}',
        "--json",
    )
    assert result.exit_code == 0


def test_broadcast_team_message_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=1, stdout="{}", stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.broadcast_team_message(
            TeamApiBroadcastRequest(
                team_name="alpha",
                from_worker="worker-1",
                body="ACK",
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "broadcast",
        "--input",
        '{"team_name":"alpha","from_worker":"worker-1","body":"ACK"}',
        "--json",
    )
    assert result.exit_code == 1


def test_create_team_task_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=1, stdout="{}", stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.create_team_task(
            TeamApiCreateTaskRequest(
                team_name="alpha",
                subject="Demo task",
                description="Created through CLI interop",
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "create-task",
        "--input",
        '{"team_name":"alpha","subject":"Demo task","description":"Created through CLI interop"}',
        "--json",
    )
    assert result.exit_code == 1


def test_read_team_task_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=1, stdout="{}", stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.read_team_task(
            TeamApiReadTaskRequest(team_name="alpha", task_id="1")
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "read-task",
        "--input",
        '{"team_name":"alpha","task_id":"1"}',
        "--json",
    )
    assert result.exit_code == 1


def test_transition_team_task_status_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=1, stdout="{}", stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.transition_team_task_status(
            TeamApiTransitionTaskStatusRequest(
                team_name="alpha",
                task_id="1",
                from_status="in_progress",
                to_status="completed",
                claim_token="claim-token",
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "transition-task-status",
        "--input",
        '{"team_name":"alpha","task_id":"1","from":"in_progress","to":"completed","claim_token":"claim-token"}',
        "--json",
    )
    assert result.exit_code == 1


def test_update_team_task_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.update_team_task(
            TeamApiUpdateTaskRequest(
                team_name="alpha",
                task_id="1",
                subject="Refined task",
                blocked_by=[],
                requires_code_change=False,
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "update-task",
        "--input",
        '{"team_name":"alpha","task_id":"1","subject":"Refined task","blocked_by":[],"requires_code_change":false}',
        "--json",
    )
    assert result.exit_code == 0


def test_claim_team_task_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=1, stdout="{}", stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.claim_team_task(
            TeamApiClaimTaskRequest(
                team_name="alpha",
                task_id="1",
                worker="worker-1",
                expected_version=3,
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "claim-task",
        "--input",
        '{"team_name":"alpha","task_id":"1","worker":"worker-1","expected_version":3}',
        "--json",
    )
    assert result.exit_code == 1


def test_release_team_task_claim_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=1, stdout="{}", stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.release_team_task_claim(
            TeamApiReleaseTaskClaimRequest(
                team_name="alpha",
                task_id="1",
                claim_token="claim-token",
                worker="worker-1",
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "release-task-claim",
        "--input",
        '{"team_name":"alpha","task_id":"1","claim_token":"claim-token","worker":"worker-1"}',
        "--json",
    )
    assert result.exit_code == 1


def test_read_team_task_approval_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.read_team_task_approval(
            TeamApiReadTaskApprovalRequest(team_name="alpha", task_id="1")
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "read-task-approval",
        "--input",
        '{"team_name":"alpha","task_id":"1"}',
        "--json",
    )
    assert result.exit_code == 0


def test_write_team_task_approval_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=1, stdout="{}", stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.write_team_task_approval(
            TeamApiWriteTaskApprovalRequest(
                team_name="alpha",
                task_id="1",
                status="approved",
                reviewer="leader-fixed",
                decision_reason="approved in demo",
                required=True,
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "write-task-approval",
        "--input",
        '{"team_name":"alpha","task_id":"1","status":"approved","reviewer":"leader-fixed","decision_reason":"approved in demo","required":true}',
        "--json",
    )
    assert result.exit_code == 1


def test_mark_team_mailbox_delivered_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.mark_team_mailbox_delivered(
            TeamApiMailboxMarkDeliveredRequest(
                team_name="alpha",
                worker="worker-1",
                message_id="message-1",
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "mailbox-mark-delivered",
        "--input",
        '{"team_name":"alpha","worker":"worker-1","message_id":"message-1"}',
        "--json",
    )
    assert result.exit_code == 0


def test_mark_team_mailbox_notified_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.mark_team_mailbox_notified(
            TeamApiMailboxMarkNotifiedRequest(
                team_name="alpha",
                worker="worker-1",
                message_id="message-1",
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "mailbox-mark-notified",
        "--input",
        '{"team_name":"alpha","worker":"worker-1","message_id":"message-1"}',
        "--json",
    )
    assert result.exit_code == 0


def test_write_team_shutdown_request_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=1, stdout="{}", stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.write_team_shutdown_request(
            TeamApiWriteShutdownRequest(
                team_name="alpha",
                worker="worker-1",
                requested_by="leader-fixed",
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "write-shutdown-request",
        "--input",
        '{"team_name":"alpha","worker":"worker-1","requested_by":"leader-fixed"}',
        "--json",
    )
    assert result.exit_code == 1


def test_read_team_shutdown_ack_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.read_team_shutdown_ack(
            TeamApiReadShutdownAckRequest(
                team_name="alpha",
                worker="worker-1",
                min_updated_at="2026-05-05T00:00:00Z",
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "read-shutdown-ack",
        "--input",
        '{"team_name":"alpha","worker":"worker-1","min_updated_at":"2026-05-05T00:00:00Z"}',
        "--json",
    )
    assert result.exit_code == 0


def test_cleanup_team_state_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=1, stdout="{}", stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.cleanup_team_state(
            TeamApiCleanupRequest(
                team_name="alpha",
                force=True,
                confirm_issues=True,
            )
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "cleanup",
        "--input",
        '{"team_name":"alpha","force":true,"confirm_issues":true}',
        "--json",
    )
    assert result.exit_code == 1


def test_cleanup_team_orphans_runs_expected_omx_arguments(monkeypatch) -> None:
    recorded_arguments: tuple[str, ...] = ()

    def fake_run_omx_command(
        arguments: tuple[str, ...], cwd: str | None = None
    ) -> OmxCommandResult:
        nonlocal recorded_arguments
        _ = cwd
        recorded_arguments = arguments
        return OmxCommandResult(exit_code=1, stdout="{}", stderr="")

    monkeypatch.setattr(team_api_control, "run_omx_command", fake_run_omx_command)

    result = asyncio.run(
        team_api_control.cleanup_team_orphans(
            TeamApiOrphanCleanupRequest(team_name="alpha")
        )
    )

    assert recorded_arguments == (
        "team",
        "api",
        "orphan-cleanup",
        "--input",
        '{"team_name":"alpha"}',
        "--json",
    )
    assert result.exit_code == 1
