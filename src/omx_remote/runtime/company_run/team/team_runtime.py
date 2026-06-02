from pathlib import Path

from omx_remote.runtime.commands.artifacts.actual_run_record_writer import (
    ActualRunPaths,
)
from omx_remote.runtime.commands.execution.subprocess_attempt_runner import (
    run_subprocess,
    write_attempt,
)
from omx_remote.runtime.commands.planning.command_runtime_options import (
    team_worker_launch_args,
    team_worker_launch_environment_name,
)
from omx_remote.runtime.company_run.team.handoff_detection import (
    team_launch_needs_startup_handoff,
    team_launch_needs_workflow_handoff,
    team_launch_needs_workspace_handoff,
)
from omx_remote.runtime.company_run.team.team_evidence import (
    wait_for_team_completion_evidence,
)
from omx_remote.runtime.company_run.team.team_preflight import (
    team_split_worktree_preflight,
)
from omx_remote.runtime.company_run.team.team_state_identity import (
    team_name_from_launch_evidence,
    team_state_evidence_text,
)
from omx_remote.runtime.company_run.team.team_task_prompt import (
    build_team_task,
    write_worker_dispatches,
)
from omx_remote.runtime.omx_team_owner_preflight import (
    require_omx_team_live_launch_owner_support,
)
from omx_remote.schemas.commands.command_execution_schemas import (
    CommandFailureClassification,
)
from omx_remote.schemas.commands.command_runtime_option_schemas import (
    CommandRuntimeOptions,
)
from omx_remote.schemas.company_run.company_run_runtime_schemas import (
    CompanyRunTeamLaunchRecord,
)
from omx_remote.schemas.process_environment_schemas import (
    ProcessEnvironmentOverride,
    ProcessEnvironmentOverrides,
)
from omx_remote.shared.omx_enums.command_enums import CommandFailureKind
from omx_remote.shared.omx_enums.company_run_enums import CompanyRunTeamLaunchStatus


def _failure(reason: str) -> CommandFailureClassification:
    """Build a command failure classification for Team launch evidence.

    Args:
        reason [str]: Failure reason.

    Returns:
        CommandFailureClassification: Runtime conflict classification.
    """
    failure = CommandFailureClassification(
        kind=CommandFailureKind.RUNTIME_CONFLICT,
        reason=reason,
        retryable=True,
    )
    return failure


def _team_worker_environment_overrides(
    runtime_options: CommandRuntimeOptions | None,
) -> ProcessEnvironmentOverrides | None:
    """Build transient environment overrides for native OMX Team worker launch.

    Args:
        runtime_options [CommandRuntimeOptions | None]: Optional Codex runtime controls.

    Returns:
        ProcessEnvironmentOverrides | None: Environment overrides when Team worker
        launch args are needed.
    """
    launch_args = team_worker_launch_args(runtime_options=runtime_options)
    if launch_args is None:
        no_overrides: None = None
        return no_overrides
    overrides = ProcessEnvironmentOverrides(
        values=(
            ProcessEnvironmentOverride(
                name=team_worker_launch_environment_name(),
                value=launch_args,
            ),
        )
    )
    return overrides


def launch_company_run_team(
    paths: ActualRunPaths,
    cwd: Path,
    objective: str,
    company_root: Path,
    worker_count: int,
    timeout_seconds: float,
    step_index: int,
    launch_mode: str,
    runtime_options: CommandRuntimeOptions | None = None,
) -> tuple[CompanyRunTeamLaunchRecord, tuple]:
    """Launch and optionally await the OMX Team leg.

    Args:
        paths [ActualRunPaths]: Actual run paths.
        cwd [Path]: Target repository cwd.
        objective [str]: User objective.
        company_root [Path]: Company-run artifact root.
        worker_count [int]: Team worker count, minimum three.
        timeout_seconds [float]: Subprocess timeout.
        step_index [int]: Synthetic step index for attempt artifacts.
        launch_mode [str]: Whether to launch or write handoff only.
        runtime_options [CommandRuntimeOptions | None]: Optional Codex runtime controls.

    Returns:
        tuple[CompanyRunTeamLaunchRecord, tuple]: Launch record and step attempts.
    """
    dispatch_path = write_worker_dispatches(
        company_root=company_root,
        objective=objective,
        worker_count=worker_count,
    )
    team_task = build_team_task(
        objective=objective,
        company_root=company_root,
        worker_count=worker_count,
        runtime_options=runtime_options,
    )
    worker_launch_args = team_worker_launch_args(runtime_options=runtime_options)
    command_arguments: tuple[str, ...] = (
        "omx",
        "team",
        f"{worker_count}:executor",
        team_task,
    )
    if launch_mode == "handoff":
        record = CompanyRunTeamLaunchRecord(
            status=CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION,
            command=command_arguments,
            runtime_options=runtime_options,
            worker_launch_args=worker_launch_args,
            worker_count=worker_count,
            dispatch_path=str(dispatch_path),
            launch_stdout_path=str(company_root / "team" / "team-launch.stdout.txt"),
            launch_stderr_path=str(company_root / "team" / "team-launch.stderr.txt"),
            note="--team-launch handoff wrote Team dispatch but did not launch runtime.",
        )
        return record, ()
    split_preflight = team_split_worktree_preflight(cwd=cwd)
    if not split_preflight.allowed:
        record = CompanyRunTeamLaunchRecord(
            status=CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION,
            command=command_arguments,
            runtime_options=runtime_options,
            worker_launch_args=worker_launch_args,
            worker_count=worker_count,
            dispatch_path=str(dispatch_path),
            launch_stdout_path=str(company_root / "team" / "team-launch.stdout.txt"),
            launch_stderr_path=str(company_root / "team" / "team-launch.stderr.txt"),
            note=(
                "OMX Team launch blocked before worker split because the leader "
                "worktree is not clean; create a clean snapshot, commit, or stash "
                f"before Team fanout. git status: {split_preflight.detail}"
            ),
        )
        return record, ()
    try:
        require_omx_team_live_launch_owner_support(
            launch_context="company-run live OMX Team launch",
        )
    except ValueError as error:
        record = CompanyRunTeamLaunchRecord(
            status=CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION,
            command=command_arguments,
            runtime_options=runtime_options,
            worker_launch_args=worker_launch_args,
            worker_count=worker_count,
            dispatch_path=str(dispatch_path),
            launch_stdout_path=str(company_root / "team" / "team-launch.stdout.txt"),
            launch_stderr_path=str(company_root / "team" / "team-launch.stderr.txt"),
            note=str(error),
        )
        return record, ()

    environment_overrides = _team_worker_environment_overrides(
        runtime_options=runtime_options,
    )
    if environment_overrides is None:
        launch_outcome = run_subprocess(
            argv=command_arguments,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
    else:
        launch_outcome = run_subprocess(
            argv=command_arguments,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            environment_overrides=environment_overrides,
        )
    launch_failure = None
    if launch_outcome.exit_code != 0 or launch_outcome.timed_out:
        launch_failure = _failure(
            "company-run OMX Team launch did not complete successfully"
        )
    launch_attempt = write_attempt(
        paths=paths,
        step_index=step_index,
        attempt=1,
        outcome=launch_outcome,
        classification=launch_failure,
    )
    combined_output = f"{launch_outcome.stdout}\n{launch_outcome.stderr}"
    team_name = team_name_from_launch_evidence(cwd=cwd, output=combined_output)
    team_state_evidence = team_state_evidence_text(cwd=cwd, team_name=team_name)
    combined_evidence = f"{combined_output}\n{team_state_evidence}"
    status = CompanyRunTeamLaunchStatus.LAUNCHED
    note = "OMX Team launch command exited successfully."
    await_attempt = None
    await_exit_code = None
    await_stdout_path = None
    await_stderr_path = None

    if launch_failure is not None:
        if team_launch_needs_workspace_handoff(combined_evidence):
            status = CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION
            note = (
                "OMX Team launch is blocked by a dirty leader worktree; "
                "commit or stash before live Team fanout."
            )
        elif team_launch_needs_startup_handoff(combined_evidence):
            status = CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION
            note = (
                "OMX Team launch reached worker startup but a worker did not become "
                "ready before the readiness timeout; inspect Team/tmux startup state."
            )
        elif team_launch_needs_workflow_handoff(combined_evidence):
            status = CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION
            note = (
                "OMX Team launch is blocked by active OMX workflow state; clear or "
                "isolate incompatible modes before live Team fanout."
            )
        elif team_name is not None and launch_outcome.exit_code is not None:
            status = CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION
            note = (
                "OMX Team state was created but the launch process exited before "
                "a clean await handoff; inspect Team state and resume or shutdown."
            )
        else:
            status = CompanyRunTeamLaunchStatus.FAILED
            note = "OMX Team launch failed; see captured stdout/stderr."
    elif team_name is None:
        status = CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION
        note = "OMX Team launched or returned successfully, but no team name was detected for await/status follow-up."
    else:
        await_ms = str(max(1000, int(timeout_seconds * 1000)))
        await_arguments: tuple[str, ...] = (
            "omx",
            "team",
            "await",
            team_name,
            "--timeout-ms",
            await_ms,
            "--json",
        )
        await_outcome = run_subprocess(
            argv=await_arguments,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
        await_failure = None
        if await_outcome.exit_code != 0 or await_outcome.timed_out:
            await_failure = _failure(
                "company-run OMX Team await did not reach a clean terminal event"
            )
        await_attempt = write_attempt(
            paths=paths,
            step_index=step_index,
            attempt=2,
            outcome=await_outcome,
            classification=await_failure,
        )
        await_exit_code = await_outcome.exit_code
        await_stdout_path = await_attempt.stdout_path
        await_stderr_path = await_attempt.stderr_path
        if await_failure is None:
            completion_evidence = wait_for_team_completion_evidence(
                cwd=cwd,
                team_name=team_name,
                timeout_seconds=timeout_seconds,
            )
            if completion_evidence.complete:
                status = CompanyRunTeamLaunchStatus.COMPLETED
                note = (
                    "OMX Team launched, await returned cleanly, and Team state "
                    f"shows all tasks completed. {completion_evidence.detail}"
                )
            else:
                status = CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION
                if completion_evidence.terminal:
                    note = (
                        "OMX Team await returned cleanly, but Team status is now "
                        "missing; treat this as cleanup/stale notification evidence "
                        "rather than actionable worker work. "
                        f"{completion_evidence.detail}"
                    )
                else:
                    note = (
                        "OMX Team await returned cleanly, but Team state does not show "
                        f"completed worker output. {completion_evidence.detail}"
                    )
        else:
            status = CompanyRunTeamLaunchStatus.REQUIRES_AGENT_ACTION
            note = "OMX Team launch succeeded, but await needs follow-up; see await artifacts."

    attempts = (
        (launch_attempt,) if await_attempt is None else (launch_attempt, await_attempt)
    )
    record = CompanyRunTeamLaunchRecord(
        status=status,
        command=command_arguments,
        runtime_options=runtime_options,
        worker_launch_args=worker_launch_args,
        worker_count=worker_count,
        team_name=team_name,
        dispatch_path=str(dispatch_path),
        launch_stdout_path=launch_attempt.stdout_path,
        launch_stderr_path=launch_attempt.stderr_path,
        await_stdout_path=await_stdout_path,
        await_stderr_path=await_stderr_path,
        exit_code=launch_outcome.exit_code,
        await_exit_code=await_exit_code,
        note=note,
    )
    return record, attempts
