from __future__ import annotations

import json
import subprocess
from importlib import import_module
from pathlib import Path

from omx_agent_adapter_cli import app
from typer.testing import CliRunner

from omx_remote.shared.omx_enums.company_run_enums import CompanyRunTeamLaunchMode
from omx_remote.shared.utils.json_model_dump import model_json_object


def _attr(module_name: str, attr_name: str) -> object:
    module = import_module(module_name)
    assert hasattr(module, attr_name), f"{module_name}.{attr_name} is required"
    return getattr(module, attr_name)


def _init_clean_git_repo(path: Path) -> None:
    subprocess.run(("git", "init", "-q"), cwd=path, check=True)
    subprocess.run(
        ("git", "config", "user.name", "company-run-test"),
        cwd=path,
        check=True,
    )
    subprocess.run(
        ("git", "config", "user.email", "company-run-test@example.invalid"),
        cwd=path,
        check=True,
    )
    (path / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    subprocess.run(("git", "add", "tracked.txt"), cwd=path, check=True)
    subprocess.run(
        ("git", "commit", "-q", "-m", "initial"),
        cwd=path,
        check=True,
    )


def test_cli_execute_company_run_passes_explicit_company_options(
    monkeypatch,
    tmp_path: Path,
) -> None:
    engine_module = import_module("omx_remote.runtime.company_run.engine")
    result_schema = _attr("omx_remote.schemas.company_run_schemas", "CompanyRunResult")
    calls: list[dict[str, object]] = []

    def fake_execute_company_run(request):
        request_payload = model_json_object(request)
        calls.append(request_payload)
        run_dir = tmp_path / ".comx-agent" / "runs" / "fake-company-run"
        company_root = run_dir / "company-run"
        company_root.mkdir(parents=True)
        result_path = run_dir / "result.json"
        payload = {
            "run_id": "fake-company-run",
            "command_id": "company-run",
            "qualified_id": "builtin:company-run",
            "cwd": str(tmp_path.resolve()),
            "dry_run": False,
            "status": "succeeded",
            "run_dir": str(run_dir),
            "result_path": str(result_path),
            "company_run_root": str(company_root),
            "blocked_reasons": [],
            "team_launch_attempted": False,
            "team_task": None,
            "artifacts": [str(company_root / "state.json")],
            "runtime_options": request_payload["runtime_options"],
            "metadata": {},
        }
        result = result_schema.model_validate(payload)  # type: ignore[attr-defined]
        result_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result

    monkeypatch.setattr(engine_module, "execute_company_run", fake_execute_company_run)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run",
            "builtin:company-run",
            "--cwd",
            str(tmp_path),
            "--execute",
            "--autonomy",
            "agent",
            "--task",
            "ship the company-run engine",
            "--council-mode",
            "artifact",
            "--team-launch",
            "handoff",
            "--worker-count",
            "6",
            "--live-team",
            "--model",
            "gpt-5.5",
            "--xhigh",
            "--madmax",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "objective": "ship the company-run engine",
            "cwd": str(tmp_path.resolve()),
            "autonomy": "agent",
            "notes": None,
            "council_mode": "artifact",
            "live_team_allowed": True,
            "team_launch_mode": "handoff",
            "worker_count": 6,
            "max_research_rounds": 2,
            "timeout_seconds": 1800.0,
            "runtime_options": {
                "model": "gpt-5.5",
                "reasoning_effort": "xhigh",
                "madmax": True,
            },
        }
    ]
    assert "fake-company-run" in result.output
    assert '"runtime_options": {' in result.output
    assert '"dry_run": false' in result.output


def test_company_run_engine_uses_injected_team_launcher_and_never_shells_real_team(
    monkeypatch,
    tmp_path: Path,
) -> None:
    engine_module = import_module("omx_remote.runtime.company_run.engine")
    request_schema = _attr(
        "omx_remote.schemas.company_run_schemas",
        "CompanyRunExecutionRequest",
    )
    engine_class = _attr("omx_remote.runtime.company_run.engine", "CompanyRunEngine")
    launched_commands: list[tuple[str, ...]] = []
    validated_vote_counts: list[int] = []

    def fake_team_launcher(team_request):
        launched_commands.append(tuple(team_request.native_argv))
        return {
            "status": "planned",
            "native_argv": team_request.native_argv,
            "workers": team_request.worker_count,
        }

    def fake_validate_vote_authorship(votes):
        validated_vote_counts.append(len(votes))

    monkeypatch.setattr(
        engine_module,
        "validate_vote_authorship",
        fake_validate_vote_authorship,
    )
    request = request_schema.model_validate(  # type: ignore[attr-defined]
        {
            "objective": "prove dispatch is injectable",
            "cwd": str(tmp_path),
            "autonomy": "agent",
            "council_mode": "artifact",
            "live_team_allowed": False,
        }
    )
    engine = engine_class(team_launcher=fake_team_launcher)  # type: ignore[operator]

    result = engine.execute(request)

    assert result.dry_run is False
    assert result.status in {"succeeded", "requires_agent_action"}
    assert launched_commands == [("omx", "team", "4:executor", result.team_task)]
    assert validated_vote_counts == [3]

    artifact_index_path = Path(result.metadata["artifact_index_path"])
    artifact_index = json.loads(artifact_index_path.read_text())
    required_artifacts = [
        artifact for artifact in artifact_index["artifacts"] if artifact["required"]
    ]
    assert required_artifacts
    assert all(artifact["exists"] for artifact in required_artifacts)


def test_company_run_request_defaults_to_no_runtime_options(tmp_path: Path) -> None:
    request_schema = _attr(
        "omx_remote.schemas.company_run_schemas",
        "CompanyRunExecutionRequest",
    )

    request = request_schema.model_validate(  # type: ignore[attr-defined]
        {
            "objective": "prove default company-run behavior is unchanged",
            "cwd": str(tmp_path),
            "autonomy": "agent",
            "council_mode": "artifact",
            "live_team_allowed": False,
        }
    )

    payload = model_json_object(request)
    assert payload["runtime_options"] is None
    assert payload["team_launch_mode"] == "launch"
    assert payload["worker_count"] == 4


def test_company_run_preserves_runtime_options_in_result_and_team_records(
    tmp_path: Path,
) -> None:
    request_schema = _attr(
        "omx_remote.schemas.company_run_schemas",
        "CompanyRunExecutionRequest",
    )
    engine_class = _attr("omx_remote.runtime.company_run.engine", "CompanyRunEngine")
    launched_requests: list[dict[str, object]] = []
    expected_options = {
        "model": "gpt-5.5",
        "reasoning_effort": "xhigh",
        "madmax": True,
    }

    def fake_team_launcher(team_request) -> None:
        launched_requests.append(model_json_object(team_request))

    request = request_schema.model_validate(  # type: ignore[attr-defined]
        {
            "objective": "prove runtime options survive company-run handoff",
            "cwd": str(tmp_path),
            "autonomy": "agent",
            "council_mode": "artifact",
            "live_team_allowed": False,
            "runtime_options": expected_options,
        }
    )
    engine = engine_class(team_launcher=fake_team_launcher)  # type: ignore[operator]

    result = engine.execute(request)

    result_payload = model_json_object(result)
    state_path = Path(result.metadata["state_path"])
    state_payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert result_payload["runtime_options"] == expected_options
    assert launched_requests[0]["runtime_options"] == expected_options
    assert state_payload["team_launch"]["runtime_options"] == expected_options
    assert launched_requests[0]["native_argv"][:3] == [
        "omx",
        "team",
        "4:executor",
    ]


def test_company_run_default_codex_council_blocks_when_subagents_fail(
    monkeypatch,
    tmp_path: Path,
) -> None:
    council_module = import_module(
        "omx_remote.runtime.company_run.company_run_council_runtime"
    )
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    request_schema = _attr(
        "omx_remote.schemas.company_run_schemas",
        "CompanyRunExecutionRequest",
    )
    engine_class = _attr("omx_remote.runtime.company_run.engine", "CompanyRunEngine")
    launched_requests: list[object] = []

    def failing_codex_run(argv, cwd, timeout_seconds):
        return outcome_schema(  # type: ignore[operator]
            argv=argv,
            started_at="2026-06-01T00:00:00Z",
            finished_at="2026-06-01T00:00:01Z",
            duration_seconds=1.0,
            exit_code=127,
            stdout="",
            stderr="codex unavailable",
            timed_out=False,
        )

    monkeypatch.setattr(council_module, "run_subprocess", failing_codex_run)
    request = request_schema.model_validate(  # type: ignore[attr-defined]
        {
            "objective": "prove codex council is mandatory by default",
            "cwd": str(tmp_path),
            "autonomy": "agent",
            "live_team_allowed": False,
        }
    )
    engine = engine_class(team_launcher=launched_requests.append)  # type: ignore[operator]

    result = engine.execute(request)

    assert result.status == "blocked"
    assert result.team_launch_attempted is False
    assert launched_requests == []
    assert result.blocked_reasons


def test_company_run_artifact_council_mode_does_not_invoke_codex_subprocess(
    monkeypatch,
    tmp_path: Path,
) -> None:
    council_module = import_module(
        "omx_remote.runtime.company_run.company_run_council_runtime"
    )
    request_schema = _attr(
        "omx_remote.schemas.company_run_schemas",
        "CompanyRunExecutionRequest",
    )
    engine_class = _attr("omx_remote.runtime.company_run.engine", "CompanyRunEngine")
    launched_requests: list[object] = []

    def forbidden_codex_run(*args, **kwargs):
        raise AssertionError("artifact council mode must not invoke Codex subprocess")

    monkeypatch.setattr(council_module, "run_subprocess", forbidden_codex_run)
    request = request_schema.model_validate(  # type: ignore[attr-defined]
        {
            "objective": "prove artifact council mode is explicit",
            "cwd": str(tmp_path),
            "autonomy": "agent",
            "council_mode": "artifact",
            "live_team_allowed": False,
        }
    )
    engine = engine_class(team_launcher=launched_requests.append)  # type: ignore[operator]

    result = engine.execute(request)

    assert result.status == "requires_agent_action"
    assert len(launched_requests) == 1


def test_company_run_live_team_dirty_worktree_requires_agent_action(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.company_run_team_runtime"
    )
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.company_run_result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.company_run_team_runtime",
        "launch_company_run_team",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "dirty-team"
    run_dir.mkdir(parents=True)
    paths = actual_paths("dirty-team", run_dir)  # type: ignore[operator]
    for path in (
        paths.stdout_log_path,
        paths.stderr_log_path,
    ):
        path.write_text("", encoding="utf-8")

    def dirty_worktree_team_run(argv, cwd, timeout_seconds):
        return outcome_schema(  # type: ignore[operator]
            argv=argv,
            started_at="2026-06-01T00:00:00Z",
            finished_at="2026-06-01T00:00:01Z",
            duration_seconds=1.0,
            exit_code=1,
            stdout="",
            stderr="leader_workspace_dirty_for_worktrees: commit_or_stash_before_omx_team",
            timed_out=False,
        )

    monkeypatch.setattr(team_module, "run_subprocess", dirty_worktree_team_run)

    record, _attempts = launch_team(  # type: ignore[operator]
        paths=paths,
        cwd=tmp_path,
        objective="prove dirty worktree is a handoff blocker",
        company_root=run_dir / "company-run",
        worker_count=4,
        timeout_seconds=1.0,
        step_index=2,
        launch_mode=CompanyRunTeamLaunchMode.LAUNCH,
    )

    assert record.status == "requires_agent_action"
    assert "dirty leader worktree" in record.note


def test_company_run_blocks_live_team_before_split_when_worktree_is_dirty(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    (tmp_path / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    team_module = import_module(
        "omx_remote.runtime.company_run.company_run_team_runtime"
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.company_run_result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.company_run_team_runtime",
        "launch_company_run_team",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "dirty-preflight-team"
    run_dir.mkdir(parents=True)
    paths = actual_paths("dirty-preflight-team", run_dir)  # type: ignore[operator]
    for path in (
        paths.stdout_log_path,
        paths.stderr_log_path,
    ):
        path.write_text("", encoding="utf-8")

    def forbidden_team_run(*args, **kwargs):
        raise AssertionError("dirty leader preflight must block before omx team")

    monkeypatch.setattr(team_module, "run_subprocess", forbidden_team_run)

    record, attempts = launch_team(  # type: ignore[operator]
        paths=paths,
        cwd=tmp_path,
        objective="prove dirty preflight blocks before Team split",
        company_root=run_dir / "company-run",
        worker_count=4,
        timeout_seconds=30.0,
        step_index=2,
        launch_mode=CompanyRunTeamLaunchMode.LAUNCH,
    )

    assert attempts == ()
    assert record.status == "requires_agent_action"
    assert "blocked before worker split" in record.note
    assert "tracked.txt" in record.note


def test_company_run_live_team_startup_timeout_requires_agent_action(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.company_run_team_runtime"
    )
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.company_run_result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.company_run_team_runtime",
        "launch_company_run_team",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "startup-timeout-team"
    run_dir.mkdir(parents=True)
    paths = actual_paths("startup-timeout-team", run_dir)  # type: ignore[operator]
    for path in (
        paths.stdout_log_path,
        paths.stderr_log_path,
    ):
        path.write_text("", encoding="utf-8")

    def startup_timeout_team_run(argv, cwd, timeout_seconds):
        return outcome_schema(  # type: ignore[operator]
            argv=argv,
            started_at="2026-06-01T00:00:00Z",
            finished_at="2026-06-01T00:00:01Z",
            duration_seconds=1.0,
            exit_code=1,
            stdout="[omx:team] worker startup resolution: model=gpt-5.5",
            stderr="Error: Worker worker-1 did not become ready in tmux session team:0",
            timed_out=False,
        )

    monkeypatch.setattr(team_module, "run_subprocess", startup_timeout_team_run)

    record, _attempts = launch_team(  # type: ignore[operator]
        paths=paths,
        cwd=tmp_path,
        objective="prove startup timeout is a handoff blocker",
        company_root=run_dir / "company-run",
        worker_count=4,
        timeout_seconds=30.0,
        step_index=2,
        launch_mode=CompanyRunTeamLaunchMode.LAUNCH,
    )

    assert record.status == "requires_agent_action"
    assert "did not become ready" in record.note


def test_company_run_live_team_reads_state_when_launch_output_lacks_team_name(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.company_run_team_runtime"
    )
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.company_run_result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.company_run_team_runtime",
        "launch_company_run_team",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "state-backed-team"
    run_dir.mkdir(parents=True)
    paths = actual_paths("state-backed-team", run_dir)  # type: ignore[operator]
    for path in (
        paths.stdout_log_path,
        paths.stderr_log_path,
    ):
        path.write_text("", encoding="utf-8")

    def state_backed_team_run(argv, cwd, timeout_seconds):
        team_state = (
            Path(cwd) / ".omx" / "state" / "team" / "company-run-implement-state-backed"
        )
        worker_state = team_state / "workers" / "worker-1" / "status.json"
        events = team_state / "events" / "events.ndjson"
        worker_state.parent.mkdir(parents=True, exist_ok=True)
        events.parent.mkdir(parents=True, exist_ok=True)
        worker_state.write_text(
            '{"state":"unknown","reason":"ready_prompt_timeout"}',
            encoding="utf-8",
        )
        events.write_text(
            '{"type":"worker_state_changed","reason":"ready_prompt_timeout"}\n',
            encoding="utf-8",
        )
        return outcome_schema(  # type: ignore[operator]
            argv=argv,
            started_at="2026-06-01T00:00:00Z",
            finished_at="2026-06-01T00:00:01Z",
            duration_seconds=1.0,
            exit_code=-15,
            stdout="[omx:team] worker startup resolution: model=gpt-5.5",
            stderr="",
            timed_out=False,
        )

    monkeypatch.setattr(team_module, "run_subprocess", state_backed_team_run)

    record, _attempts = launch_team(  # type: ignore[operator]
        paths=paths,
        cwd=tmp_path,
        objective="prove Team state can identify startup handoff",
        company_root=run_dir / "company-run",
        worker_count=4,
        timeout_seconds=30.0,
        step_index=2,
        launch_mode=CompanyRunTeamLaunchMode.LAUNCH,
    )

    assert record.status == "requires_agent_action"
    assert record.team_name == "company-run-implement-state-backed"
    assert "did not become ready" in record.note


def test_company_run_live_team_await_success_requires_completed_team_tasks(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.company_run_team_runtime"
    )
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.company_run_result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.company_run_team_runtime",
        "launch_company_run_team",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "await-pending-team"
    run_dir.mkdir(parents=True)
    paths = actual_paths("await-pending-team", run_dir)  # type: ignore[operator]
    for path in (
        paths.stdout_log_path,
        paths.stderr_log_path,
    ):
        path.write_text("", encoding="utf-8")

    def await_success_with_pending_tasks(argv, cwd, timeout_seconds):
        team_state = (
            Path(cwd) / ".omx" / "state" / "team" / "company-run-implement-pending"
        )
        tasks = team_state / "tasks"
        tasks.mkdir(parents=True, exist_ok=True)
        (tasks / "task-1.json").write_text(
            '{"id":"1","status":"completed","owner":"worker-1"}',
            encoding="utf-8",
        )
        (tasks / "task-2.json").write_text(
            '{"id":"2","status":"pending","owner":"worker-2"}',
            encoding="utf-8",
        )
        return outcome_schema(  # type: ignore[operator]
            argv=argv,
            started_at="2026-06-01T00:00:00Z",
            finished_at="2026-06-01T00:00:01Z",
            duration_seconds=1.0,
            exit_code=0,
            stdout="team name: company-run-implement-pending",
            stderr="",
            timed_out=False,
        )

    monkeypatch.setattr(team_module, "run_subprocess", await_success_with_pending_tasks)

    record, attempts = launch_team(  # type: ignore[operator]
        paths=paths,
        cwd=tmp_path,
        objective="prove await success is not enough without completed tasks",
        company_root=run_dir / "company-run",
        worker_count=4,
        timeout_seconds=1.0,
        step_index=2,
        launch_mode=CompanyRunTeamLaunchMode.LAUNCH,
    )

    assert len(attempts) == 2
    assert record.status == "requires_agent_action"
    assert record.team_name == "company-run-implement-pending"
    assert "does not show completed worker output" in record.note
    assert "1/2 completed" in record.note


def test_company_run_live_team_completed_requires_all_tasks_complete(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.company_run_team_runtime"
    )
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.company_run_result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.company_run_team_runtime",
        "launch_company_run_team",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "await-completed-team"
    run_dir.mkdir(parents=True)
    paths = actual_paths("await-completed-team", run_dir)  # type: ignore[operator]
    for path in (
        paths.stdout_log_path,
        paths.stderr_log_path,
    ):
        path.write_text("", encoding="utf-8")

    def await_success_with_completed_tasks(argv, cwd, timeout_seconds):
        team_state = (
            Path(cwd) / ".omx" / "state" / "team" / "company-run-implement-completed"
        )
        tasks = team_state / "tasks"
        tasks.mkdir(parents=True, exist_ok=True)
        (tasks / "task-1.json").write_text(
            '{"id":"1","status":"completed","owner":"worker-1"}',
            encoding="utf-8",
        )
        (tasks / "task-2.json").write_text(
            '{"id":"2","status":"done","owner":"worker-2"}',
            encoding="utf-8",
        )
        return outcome_schema(  # type: ignore[operator]
            argv=argv,
            started_at="2026-06-01T00:00:00Z",
            finished_at="2026-06-01T00:00:01Z",
            duration_seconds=1.0,
            exit_code=0,
            stdout="team name: company-run-implement-completed",
            stderr="",
            timed_out=False,
        )

    monkeypatch.setattr(
        team_module, "run_subprocess", await_success_with_completed_tasks
    )

    record, attempts = launch_team(  # type: ignore[operator]
        paths=paths,
        cwd=tmp_path,
        objective="prove completed tasks are required for completed Team status",
        company_root=run_dir / "company-run",
        worker_count=4,
        timeout_seconds=30.0,
        step_index=2,
        launch_mode=CompanyRunTeamLaunchMode.LAUNCH,
    )

    assert len(attempts) == 2
    assert record.status == "completed"
    assert record.team_name == "company-run-implement-completed"
    assert "all tasks completed" in record.note


def test_company_run_live_team_workflow_overlap_requires_agent_action(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.company_run_team_runtime"
    )
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.company_run_result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.company_run_team_runtime",
        "launch_company_run_team",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "workflow-overlap-team"
    run_dir.mkdir(parents=True)
    paths = actual_paths("workflow-overlap-team", run_dir)  # type: ignore[operator]
    for path in (
        paths.stdout_log_path,
        paths.stderr_log_path,
    ):
        path.write_text("", encoding="utf-8")

    def workflow_overlap_team_run(argv, cwd, timeout_seconds):
        return outcome_schema(  # type: ignore[operator]
            argv=argv,
            started_at="2026-06-01T00:00:00Z",
            finished_at="2026-06-01T00:00:01Z",
            duration_seconds=1.0,
            exit_code=1,
            stdout="[omx:team] worker startup resolution: model=gpt-5.5",
            stderr="Cannot start team: ultrawork and ultragoal are already active. Unsupported workflow overlap: ultrawork + ultragoal + team.",
            timed_out=False,
        )

    monkeypatch.setattr(team_module, "run_subprocess", workflow_overlap_team_run)

    record, _attempts = launch_team(  # type: ignore[operator]
        paths=paths,
        cwd=tmp_path,
        objective="prove workflow overlap is a handoff blocker",
        company_root=run_dir / "company-run",
        worker_count=4,
        timeout_seconds=30.0,
        step_index=2,
        launch_mode=CompanyRunTeamLaunchMode.LAUNCH,
    )

    assert record.status == "requires_agent_action"
    assert "active OMX workflow state" in record.note


def test_company_run_dry_run_remains_preview_only(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "run",
            "builtin:company-run",
            "--cwd",
            str(tmp_path),
            "--dry-run",
            "--task",
            "preview company-run without actual execution",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    assert '"command_id": "company-run"' in result.output
    assert '"dry_run": true' in result.output
    assert "preview company-run without actual execution" in result.output


def test_company_run_vote_ballot_evidence_paths_exist(
    monkeypatch, tmp_path: Path
) -> None:
    request_schema = _attr(
        "omx_remote.schemas.company_run_schemas",
        "CompanyRunExecutionRequest",
    )
    engine_class = _attr("omx_remote.runtime.company_run.engine", "CompanyRunEngine")
    launched_requests: list[object] = []

    request = request_schema.model_validate(  # type: ignore[attr-defined]
        {
            "objective": "prove ballot evidence paths point at produced artifacts",
            "cwd": str(tmp_path),
            "autonomy": "agent",
            "council_mode": "artifact",
            "live_team_allowed": False,
        }
    )
    engine = engine_class(team_launcher=launched_requests.append)  # type: ignore[operator]

    result = engine.execute(request)

    state_path = Path(result.metadata["state_path"])
    state_payload = json.loads(state_path.read_text(encoding="utf-8"))
    evidence_paths = tuple(
        Path(ballot["evidence_path"])
        for vote in state_payload["votes"]
        for ballot in vote["ballots"]
    )

    assert evidence_paths
    assert all(path.is_file() for path in evidence_paths)
    assert {path.name for path in evidence_paths} >= {
        "domain-research.md",
        "risk-security.md",
        "cto-review.md",
        "ciso-security-review.md",
        "qa-review.md",
    }


def test_company_run_planned_dispatch_matches_requested_worker_count(
    monkeypatch,
    tmp_path: Path,
) -> None:
    request_schema = _attr(
        "omx_remote.schemas.company_run_schemas",
        "CompanyRunExecutionRequest",
    )
    engine_class = _attr("omx_remote.runtime.company_run.engine", "CompanyRunEngine")

    request = request_schema.model_validate(  # type: ignore[attr-defined]
        {
            "objective": "prove every planned worker gets a dispatch packet",
            "cwd": str(tmp_path),
            "autonomy": "agent",
            "council_mode": "artifact",
            "live_team_allowed": False,
            "worker_count": 8,
        }
    )
    engine = engine_class()  # type: ignore[operator]

    result = engine.execute(request)

    dispatch_path = Path(result.company_run_root) / "team" / "worker-dispatches.json"
    dispatch_payload = json.loads(dispatch_path.read_text(encoding="utf-8"))
    workers = dispatch_payload["workers"]
    assert len(workers) == 8
    assert workers[-1]["worker"] == "worker-8"
    assert "extension slice 2" in workers[-1]["ownership_boundary"]


def test_company_run_injected_launcher_sees_worker_dispatches_before_launch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    request_schema = _attr(
        "omx_remote.schemas.company_run_schemas",
        "CompanyRunExecutionRequest",
    )
    engine_class = _attr("omx_remote.runtime.company_run.engine", "CompanyRunEngine")
    dispatch_counts_at_launch: list[int] = []

    def fake_team_launcher(_team_request):
        dispatch_paths = tuple(
            tmp_path.glob(
                ".comx-agent/runs/*/company-run/team/worker-dispatches.json"
            )
        )
        assert len(dispatch_paths) == 1
        dispatch_payload = json.loads(dispatch_paths[0].read_text(encoding="utf-8"))
        workers = dispatch_payload["workers"]
        dispatch_counts_at_launch.append(len(workers))
        assert workers[-1]["worker"] == "worker-8"
        assert "extension slice 2" in workers[-1]["ownership_boundary"]

    request = request_schema.model_validate(  # type: ignore[attr-defined]
        {
            "objective": "prove injected launch sees complete dispatch packets",
            "cwd": str(tmp_path),
            "autonomy": "agent",
            "council_mode": "artifact",
            "live_team_allowed": False,
            "worker_count": 8,
        }
    )
    engine = engine_class(team_launcher=fake_team_launcher)  # type: ignore[operator]

    result = engine.execute(request)

    dispatch_path = Path(result.company_run_root) / "team" / "worker-dispatches.json"
    dispatch_payload = json.loads(dispatch_path.read_text(encoding="utf-8"))
    assert dispatch_counts_at_launch == [8]
    assert len(dispatch_payload["workers"]) == 8


def test_company_run_live_dispatch_matches_requested_worker_count(
    tmp_path: Path,
) -> None:
    actual_paths = _attr(
        "omx_remote.runtime.company_run.company_run_result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.company_run_team_runtime",
        "launch_company_run_team",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "live-dispatch-count"
    company_root = run_dir / "company-run"
    run_dir.mkdir(parents=True)
    paths = actual_paths("live-dispatch-count", run_dir)  # type: ignore[operator]
    for path in (paths.stdout_log_path, paths.stderr_log_path):
        path.write_text("", encoding="utf-8")

    record, attempts = launch_team(  # type: ignore[operator]
        paths=paths,
        cwd=tmp_path,
        objective="prove every live worker gets a dispatch packet",
        company_root=company_root,
        worker_count=8,
        timeout_seconds=1.0,
        step_index=2,
        launch_mode=CompanyRunTeamLaunchMode.LAUNCH,
    )

    dispatch_payload = json.loads(
        (company_root / "team" / "worker-dispatches.json").read_text(encoding="utf-8")
    )
    workers = dispatch_payload["workers"]
    assert attempts == ()
    assert record.worker_count == 8
    assert len(workers) == 8
    assert workers[-1]["worker"] == "worker-8"
    assert "extension slice 2" in workers[-1]["ownership_boundary"]
