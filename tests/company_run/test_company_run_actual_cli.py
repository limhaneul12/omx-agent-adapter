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


def _allow_company_run_owner_preflight(monkeypatch, team_module) -> None:
    monkeypatch.setattr(
        team_module,
        "require_omx_team_live_launch_owner_support",
        lambda *, launch_context: None,
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
            "metadata": {"state_path": str(company_root / "state.json"), "artifact_index_path": str(company_root / "artifact-index.json")},
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
            "discovery_profile": "standard",
            "max_discovery_questions": None,
            "budget_hint": None,
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
            "objective": "prove dispatch is injectable with non-goals do not mutate outside test scope, decision boundaries preserve test scope, and Team review release evidence",
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

    artifact_index_path = Path(result.metadata.artifact_index_path)
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
    assert payload["discovery_profile"] == "standard"


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
            "objective": "prove runtime options survive company-run handoff with non-goals do not mutate outside test scope, decision boundaries preserve test scope, and Team review release evidence",
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
    state_path = Path(result.metadata.state_path)
    state_payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert result_payload["runtime_options"] == expected_options
    assert launched_requests[0]["runtime_options"] == expected_options
    assert state_payload["team_launch"]["runtime_options"] == expected_options
    assert launched_requests[0]["native_argv"][:3] == [
        "omx",
        "team",
        "4:executor",
    ]


def test_company_run_team_task_prioritizes_objective_implementation(
    tmp_path: Path,
) -> None:
    build_team_task = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
        "build_team_task",
    )
    company_root = tmp_path / ".comx-agent" / "runs" / "team-task" / "company-run"

    task_text = build_team_task(  # type: ignore[operator]
        objective="improve the TUI command cockpit",
        company_root=company_root,
        worker_count=4,
    )

    backlog_index = task_text.index("## Team execution backlog")
    guardrail_index = task_text.index("## Guardrails, not standalone tasks")
    artifacts_index = task_text.index("## Artifacts to read before editing")
    assert backlog_index < guardrail_index < artifacts_index
    assert "Treat only the bullet lines in this section" in task_text
    assert "Requested native Team worker count: 4" in task_text
    assert "Do not create standalone Team tasks from" not in task_text
    assert "\n1. Worker 1 owns" not in task_text
    assert "- [worker-1] alpha-surface-ui:" in task_text
    assert "- [worker-2] beta-runtime-data:" in task_text
    assert "- [worker-3] gamma-qa-security:" in task_text
    assert "- [worker-4] delta-integration-release:" in task_text
    assert "Preserve one task per owner" in task_text
    assert "These paths are reference inputs and readiness gates, not task IDs" in (
        task_text
    )


def test_company_run_default_codex_council_blocks_when_subagents_fail(
    monkeypatch,
    tmp_path: Path,
) -> None:
    council_module = import_module(
        "omx_remote.runtime.company_run.governance.council_runtime"
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
            "objective": "prove codex council is mandatory by default with non-goals do not mutate outside test scope, decision boundaries preserve test scope, and Team review release evidence",
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
        "omx_remote.runtime.company_run.governance.council_runtime"
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
            "objective": "prove artifact council mode is explicit with non-goals do not mutate outside test scope, decision boundaries preserve test scope, and Team review release evidence",
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
        "omx_remote.runtime.company_run.team.team_runtime"
    )
    _allow_company_run_owner_preflight(monkeypatch, team_module)
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.artifacts.result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
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
        "omx_remote.runtime.company_run.team.team_runtime"
    )
    _allow_company_run_owner_preflight(monkeypatch, team_module)
    actual_paths = _attr(
        "omx_remote.runtime.company_run.artifacts.result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
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


def test_company_run_blocks_live_team_when_owner_preservation_is_unsupported(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.team.team_runtime"
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.artifacts.result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
        "launch_company_run_team",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "owner-preflight-team"
    run_dir.mkdir(parents=True)
    paths = actual_paths("owner-preflight-team", run_dir)  # type: ignore[operator]
    for path in (
        paths.stdout_log_path,
        paths.stderr_log_path,
    ):
        path.write_text("", encoding="utf-8")

    def unsupported_owner_preservation(*, launch_context):
        assert launch_context == "company-run live OMX Team launch"
        raise ValueError(
            "company-run live OMX Team launch is blocked: installed OMX does not "
            "support preserving Team DAG node.owner assignments"
        )

    def forbidden_team_run(*args, **kwargs):
        raise AssertionError("owner preflight must block before omx team")

    monkeypatch.setattr(
        team_module,
        "require_omx_team_live_launch_owner_support",
        unsupported_owner_preservation,
    )
    monkeypatch.setattr(team_module, "run_subprocess", forbidden_team_run)

    record, attempts = launch_team(  # type: ignore[operator]
        paths=paths,
        cwd=tmp_path,
        objective="prove owner preservation preflight blocks unsafe Team launch",
        company_root=run_dir / "company-run",
        worker_count=4,
        timeout_seconds=30.0,
        step_index=2,
        launch_mode=CompanyRunTeamLaunchMode.LAUNCH,
    )

    assert attempts == ()
    assert record.status == "requires_agent_action"
    assert "does not support preserving Team DAG node.owner" in record.note


def test_company_run_live_team_startup_timeout_requires_agent_action(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.team.team_runtime"
    )
    _allow_company_run_owner_preflight(monkeypatch, team_module)
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.artifacts.result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
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
        "omx_remote.runtime.company_run.team.team_runtime"
    )
    _allow_company_run_owner_preflight(monkeypatch, team_module)
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.artifacts.result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
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


def test_company_run_live_team_prefers_actual_state_team_name_over_missing_team_output(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.team.team_runtime"
    )
    _allow_company_run_owner_preflight(monkeypatch, team_module)
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.artifacts.result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
        "launch_company_run_team",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "actual-team-name"
    run_dir.mkdir(parents=True)
    paths = actual_paths("actual-team-name", run_dir)  # type: ignore[operator]
    for path in (
        paths.stdout_log_path,
        paths.stderr_log_path,
    ):
        path.write_text("", encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def launch_with_missing_team_stdout(argv, cwd, timeout_seconds):
        calls.append(tuple(argv))
        team_state = (
            Path(cwd) / ".omx" / "state" / "team" / "company-run-implement-actual"
        )
        tasks = team_state / "tasks"
        tasks.mkdir(parents=True, exist_ok=True)
        (tasks / "task-1.json").write_text(
            '{"id":"1","status":"completed","owner":"worker-1"}',
            encoding="utf-8",
        )
        (tasks / "task-2.json").write_text(
            '{"id":"2","status":"completed","owner":"worker-2"}',
            encoding="utf-8",
        )
        stdout = (
            "team name: missing-team"
            if len(calls) == 1
            else '{"status":"complete"}'
        )
        return outcome_schema(  # type: ignore[operator]
            argv=argv,
            started_at="2026-06-01T00:00:00Z",
            finished_at="2026-06-01T00:00:01Z",
            duration_seconds=1.0,
            exit_code=0,
            stdout=stdout,
            stderr="",
            timed_out=False,
        )

    monkeypatch.setattr(team_module, "run_subprocess", launch_with_missing_team_stdout)

    record, attempts = launch_team(  # type: ignore[operator]
        paths=paths,
        cwd=tmp_path,
        objective="prove launch records the concrete Team state name",
        company_root=run_dir / "company-run",
        worker_count=4,
        timeout_seconds=1.0,
        step_index=2,
        launch_mode=CompanyRunTeamLaunchMode.LAUNCH,
    )

    assert len(attempts) == 2
    assert calls[1][3] == "company-run-implement-actual"
    assert record.team_name == "company-run-implement-actual"
    assert record.team_name != "missing-team"


def test_company_run_live_team_await_success_requires_completed_team_tasks(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.team.team_runtime"
    )
    _allow_company_run_owner_preflight(monkeypatch, team_module)
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.artifacts.result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
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


def test_company_run_live_team_rejects_completed_tasks_collapsed_to_worker_one(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.team.team_runtime"
    )
    _allow_company_run_owner_preflight(monkeypatch, team_module)
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.artifacts.result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
        "launch_company_run_team",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "owner-collapse-team"
    run_dir.mkdir(parents=True)
    paths = actual_paths("owner-collapse-team", run_dir)  # type: ignore[operator]
    for path in (
        paths.stdout_log_path,
        paths.stderr_log_path,
    ):
        path.write_text("", encoding="utf-8")

    def await_success_with_worker_one_owner_collapse(argv, cwd, timeout_seconds):
        team_state = (
            Path(cwd)
            / ".omx"
            / "state"
            / "team"
            / "company-run-implement-owner-collapse"
        )
        tasks = team_state / "tasks"
        tasks.mkdir(parents=True, exist_ok=True)
        for task_id in range(1, 5):
            (tasks / f"task-{task_id}.json").write_text(
                f'{{"id":"{task_id}","status":"completed","owner":"worker-1"}}',
                encoding="utf-8",
            )
        return outcome_schema(  # type: ignore[operator]
            argv=argv,
            started_at="2026-06-01T00:00:00Z",
            finished_at="2026-06-01T00:00:01Z",
            duration_seconds=1.0,
            exit_code=0,
            stdout="team name: company-run-implement-owner-collapse",
            stderr="",
            timed_out=False,
        )

    monkeypatch.setattr(
        team_module,
        "run_subprocess",
        await_success_with_worker_one_owner_collapse,
    )

    record, attempts = launch_team(  # type: ignore[operator]
        paths=paths,
        cwd=tmp_path,
        objective="prove owner collapse cannot satisfy company-run Team completion",
        company_root=run_dir / "company-run",
        worker_count=4,
        timeout_seconds=1.0,
        step_index=2,
        launch_mode=CompanyRunTeamLaunchMode.LAUNCH,
    )

    assert len(attempts) == 2
    assert record.status == "requires_agent_action"
    assert record.team_name == "company-run-implement-owner-collapse"
    assert "1 distinct owners" in record.note
    assert "Owner distribution is invalid" in record.note


def test_company_run_live_team_missing_status_is_cleanup_warning_not_worker_followup(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.team.team_runtime"
    )
    _allow_company_run_owner_preflight(monkeypatch, team_module)
    evidence_schema = _attr(
        "omx_remote.runtime.company_run.team.team_evidence",
        "TeamStateCompletionEvidence",
    )
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.artifacts.result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
        "launch_company_run_team",
    )
    run_dir = tmp_path / ".comx-agent" / "runs" / "stale-status-team"
    run_dir.mkdir(parents=True)
    paths = actual_paths("stale-status-team", run_dir)  # type: ignore[operator]
    for path in (
        paths.stdout_log_path,
        paths.stderr_log_path,
    ):
        path.write_text("", encoding="utf-8")

    def await_success_with_stale_status(argv, cwd, timeout_seconds):
        return outcome_schema(  # type: ignore[operator]
            argv=argv,
            started_at="2026-06-01T00:00:00Z",
            finished_at="2026-06-01T00:00:01Z",
            duration_seconds=1.0,
            exit_code=0,
            stdout="team name: company-run-implement-stale-status",
            stderr="",
            timed_out=False,
        )

    def stale_status_evidence(*, cwd, team_name, timeout_seconds):
        assert team_name == "company-run-implement-stale-status"
        return evidence_schema(  # type: ignore[operator]
            complete=False,
            task_count=0,
            completed_count=0,
            blocked_count=0,
            incomplete_count=0,
            blocked_worker_count=0,
            detail=(
                "omx team status reports Team "
                "company-run-implement-stale-status is missing."
            ),
            terminal=True,
        )

    monkeypatch.setattr(team_module, "run_subprocess", await_success_with_stale_status)
    monkeypatch.setattr(
        team_module,
        "wait_for_team_completion_evidence",
        stale_status_evidence,
    )

    record, attempts = launch_team(  # type: ignore[operator]
        paths=paths,
        cwd=tmp_path,
        objective="prove missing Team status is a cleanup warning",
        company_root=run_dir / "company-run",
        worker_count=4,
        timeout_seconds=1.0,
        step_index=2,
        launch_mode=CompanyRunTeamLaunchMode.LAUNCH,
    )

    assert len(attempts) == 2
    assert record.status == "requires_agent_action"
    assert record.team_name == "company-run-implement-stale-status"
    assert "cleanup" in record.note.lower()
    assert "notification" in record.note.lower()
    assert "worker output" not in record.note
    assert "worker follow-up" not in record.note


def test_company_run_live_team_completed_requires_all_tasks_complete(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _init_clean_git_repo(tmp_path)
    team_module = import_module(
        "omx_remote.runtime.company_run.team.team_runtime"
    )
    _allow_company_run_owner_preflight(monkeypatch, team_module)
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.artifacts.result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
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
        "omx_remote.runtime.company_run.team.team_runtime"
    )
    _allow_company_run_owner_preflight(monkeypatch, team_module)
    outcome_schema = _attr(
        "omx_remote.runtime.commands.execution.subprocess_attempt_runner",
        "SubprocessAttemptOutcome",
    )
    actual_paths = _attr(
        "omx_remote.runtime.company_run.artifacts.result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
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
            "objective": "prove ballot evidence paths point at produced artifacts with non-goals do not mutate outside test scope, decision boundaries preserve test scope, and Team review release evidence",
            "cwd": str(tmp_path),
            "autonomy": "agent",
            "council_mode": "artifact",
            "live_team_allowed": False,
        }
    )
    engine = engine_class(team_launcher=launched_requests.append)  # type: ignore[operator]

    result = engine.execute(request)

    state_path = Path(result.metadata.state_path)
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
            "objective": "prove every planned worker gets a dispatch packet with non-goals do not mutate outside test scope, decision boundaries preserve test scope, and Team review release evidence",
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
            "objective": "prove injected launch sees complete dispatch packets with non-goals do not mutate outside test scope, decision boundaries preserve test scope, and Team review release evidence",
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
        "omx_remote.runtime.company_run.artifacts.result_persistence",
        "actual_company_run_paths",
    )
    launch_team = _attr(
        "omx_remote.runtime.company_run.team.team_runtime",
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
        objective="prove every live worker gets a dispatch packet with non-goals do not mutate outside test scope, decision boundaries preserve test scope, and Team review release evidence",
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
