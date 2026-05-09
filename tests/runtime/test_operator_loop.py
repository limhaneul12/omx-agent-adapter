import asyncio

from omx_remote.schemas.invoke.command_schemas import OmxCommandResult
from omx_remote.schemas.teamwork.operator_schemas import (
    TeamOperatorDispatchInstructionRequest,
    TeamOperatorDispatchOutcome,
    TeamOperatorWorkerFollowUpOutcome,
    TeamOperatorWorkerRecheckRequest,
)
from omx_remote.runtime.operators import operator_loop


def test_operate_ralph_launch_maps_success_to_observe(monkeypatch) -> None:
    monkeypatch.setattr(
        operator_loop,
        "build_ralph_launch_plan",
        lambda task, force_cleanup, allow_non_tty: (["ralph", "--prd", task], []),
    )
    monkeypatch.setattr(
        operator_loop,
        "run_omx_command",
        lambda command: OmxCommandResult(exit_code=0, stdout="ok", stderr=""),
    )

    result = operator_loop.operate_ralph_launch(
        "Ship feature",
        force_cleanup=False,
        allow_non_tty=True,
    )

    assert result.lane == "ralph"
    assert result.loop_state == "success"
    assert result.next_action == "observe"



def test_operate_ralph_resume_maps_missing_state_to_launch_hint(monkeypatch) -> None:
    def fake_build_ralph_resume_plan():
        raise ValueError(
            "No Ralph state found. Launch Ralph first or restore a resumable Ralph state."
        )

    monkeypatch.setattr(operator_loop, "build_ralph_resume_plan", fake_build_ralph_resume_plan)

    result = operator_loop.operate_ralph_resume()

    assert result.loop_state == "no_resumable_state_failure"
    assert result.next_action == "launch"
    assert result.recovery_hint is not None
    assert result.recovery_hint.next_action == "launch"



def test_operate_ralph_team_launch_maps_success_to_observe(monkeypatch) -> None:
    observed_preflight_flags: list[bool] = []

    def fake_build_ralph_team_launch_plan(
        allow_non_tty: bool,
        require_live_owner_preflight: bool = False,
    ):
        _ = allow_non_tty
        observed_preflight_flags.append(require_live_owner_preflight)
        return ["team", "3:executor", "Ship feature"], []

    monkeypatch.setattr(
        operator_loop,
        "build_ralph_team_launch_plan",
        fake_build_ralph_team_launch_plan,
    )
    monkeypatch.setattr(
        operator_loop,
        "run_omx_command",
        lambda command: OmxCommandResult(exit_code=0, stdout="ok", stderr=""),
    )

    result = operator_loop.operate_ralph_team_launch(allow_non_tty=True)

    assert result.lane == "team"
    assert result.action == "launch"
    assert result.loop_state == "success"
    assert result.next_action == "observe"
    assert observed_preflight_flags == [True]



def test_operate_ralph_team_launch_blocks_owner_unsafe_runtime_before_omx(monkeypatch) -> None:
    observed_commands: list[list[str]] = []

    def fake_build_ralph_team_launch_plan(
        allow_non_tty: bool,
        require_live_owner_preflight: bool = False,
    ):
        _ = allow_non_tty
        if require_live_owner_preflight:
            raise ValueError("installed OMX does not support preserving Team DAG node.owner")
        return ["team", "3", "Ship feature"], []

    def fake_run_omx_command(command: list[str]) -> OmxCommandResult:
        observed_commands.append(command)
        return OmxCommandResult(exit_code=0, stdout="should-not-run", stderr="")

    monkeypatch.setattr(
        operator_loop,
        "build_ralph_team_launch_plan",
        fake_build_ralph_team_launch_plan,
    )
    monkeypatch.setattr(operator_loop, "run_omx_command", fake_run_omx_command)

    result = operator_loop.operate_ralph_team_launch(allow_non_tty=True)

    assert result.lane == "team"
    assert result.action == "launch"
    assert result.loop_state == "terminal_failure"
    assert result.next_action == "escalate"
    assert result.command_result is not None
    assert "does not support preserving Team DAG node.owner" in result.command_result.stderr
    assert observed_commands == []



def test_operate_ultrawork_launch_maps_resumable_state_to_cleanup_hint(monkeypatch) -> None:
    def fake_build_ultrawork_launch_plan(
        task: str,
        *,
        force_cleanup: bool,
        allow_non_tty: bool,
        team_size: int,
        team_role: str,
    ):
        _ = (task, force_cleanup, allow_non_tty, team_size, team_role)
        raise ValueError(
            "Existing resumable Ultrawork state detected. Run `agent-remote ultrawork cleanup-stale` or retry with --force-cleanup."
        )

    monkeypatch.setattr(
        operator_loop,
        "build_ultrawork_launch_plan",
        fake_build_ultrawork_launch_plan,
    )

    result = operator_loop.operate_ultrawork_launch(
        "Run integration check",
        force_cleanup=False,
        allow_non_tty=True,
        team_size=1,
        team_role="executor",
    )

    assert result.loop_state == "stale_state_failure"
    assert result.next_action == "cleanup"
    assert result.recovery_hint is not None
    assert result.recovery_hint.cleanup_first is True



def test_operate_ralph_cleanup_returns_retry_hint(monkeypatch) -> None:
    monkeypatch.setattr(
        operator_loop,
        "cleanup_ralph_state",
        lambda workspace_root=None: ["/tmp/.omx/state/ralph-state.json"],
    )

    result = operator_loop.operate_ralph_cleanup()

    assert result.loop_state == "success"
    assert result.next_action == "retry"
    assert result.recovery_hint is not None
    assert result.recovery_hint.next_action == "retry"



def test_operate_team_instruction_maps_unverified_result_to_resumable_later(
    monkeypatch,
) -> None:
    async def fake_dispatch_team_instruction(request):
        _ = request
        return TeamOperatorDispatchOutcome(
            selected_operation="write-worker-inbox",
            outcome="accepted_but_unverified",
            needs_follow_up=True,
            reason="Mailbox write accepted but needs a read-back.",
            command_result=OmxCommandResult(exit_code=0, stdout="{}", stderr=""),
        )

    monkeypatch.setattr(
        operator_loop,
        "dispatch_team_instruction",
        fake_dispatch_team_instruction,
    )

    result = asyncio.run(
        operator_loop.operate_team_instruction(
            TeamOperatorDispatchInstructionRequest(
                team_name="alpha",
                from_worker="leader-fixed",
                to_worker="worker-1",
                body="Please re-run checks.",
                durable_delivery=True,
            )
        )
    )

    assert result.lane == "team"
    assert result.loop_state == "resumable_later"
    assert result.next_action == "observe"



def test_operate_team_worker_recheck_uses_resume_hint_for_durable_follow_up(
    monkeypatch,
) -> None:
    async def fake_request_worker_recheck(request):
        _ = request
        return TeamOperatorWorkerFollowUpOutcome(
            worker_state="unknown",
            selected_delivery_mode="durable_inbox",
            dispatch_result=TeamOperatorDispatchOutcome(
                selected_operation="write-worker-inbox",
                outcome="accepted_but_unverified",
                needs_follow_up=True,
                reason="Worker state unknown so durable inbox chosen.",
                command_result=OmxCommandResult(exit_code=0, stdout="{}", stderr=""),
            ),
        )

    monkeypatch.setattr(
        operator_loop,
        "request_worker_recheck",
        fake_request_worker_recheck,
    )

    result = asyncio.run(
        operator_loop.operate_team_worker_recheck(
            TeamOperatorWorkerRecheckRequest(
                team_name="alpha",
                from_worker="leader-fixed",
                worker="worker-1",
                body="Please re-run checks.",
            )
        )
    )

    assert result.loop_state == "resumable_later"
    assert result.next_action == "resume"
    assert result.recovery_hint is not None
    assert result.recovery_hint.next_action == "resume"
