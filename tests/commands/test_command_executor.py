import sys
from pathlib import Path

from omx_remote.runtime.commands.agent_autonomy_policy import AgentAutonomyPolicy
from omx_remote.runtime.commands.artifact_verifier import ArtifactVerifier
from omx_remote.runtime.commands.command_executor import CommandExecutor
from omx_remote.runtime.commands.command_output_redaction import redact_text
from omx_remote.runtime.commands.command_step_planner import (
    build_command_execution_plan,
)
from omx_remote.schemas.commands.command_execution_schemas import (
    CommandAutonomyDecisionKind,
)
from omx_remote.schemas.commands.command_recipe_schemas import (
    CommandRecipe,
    CommandSource,
    CommandStep,
    CommandStepCommand,
)


def _recipe(command_id: str, steps: tuple[CommandStep, ...]) -> CommandRecipe:
    recipe = CommandRecipe(
        id=command_id,
        source=CommandSource.REPO,
        description=f"Execute {command_id}.",
        steps=steps,
    )
    return recipe


def test_command_executor_runs_local_step_and_records_attempt(tmp_path: Path) -> None:
    recipe = _recipe(
        "local-ok",
        (
            CommandStep(
                command=CommandStepCommand.LOCAL,
                argv=(sys.executable, "-c", "print('ok')"),
            ),
        ),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)

    result = CommandExecutor().execute(plan, tmp_path, timestamp="20260527T010000Z")

    assert result.status == "succeeded"
    assert result.run_id == "20260527T010000Z-local-ok"
    assert result.steps[0].status == "succeeded"
    assert result.steps[0].attempts[0].exit_code == 0
    assert Path(result.result_path).exists()
    assert (
        Path(
            result.run_dir, "steps", "001", "attempts", "001", "stdout.txt"
        ).read_text()
        == "ok\n"
    )


def test_command_executor_retries_retryable_local_failure(tmp_path: Path) -> None:
    script = """
from pathlib import Path
flag = Path('attempt.flag')
if not flag.exists():
    flag.write_text('first')
    raise SystemExit(1)
print('recovered')
""".strip()
    recipe = _recipe(
        "retry-ok",
        (
            CommandStep(
                command=CommandStepCommand.LOCAL, argv=(sys.executable, "-c", script)
            ),
        ),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)

    result = CommandExecutor(max_attempts=2).execute(
        plan,
        tmp_path,
        timestamp="20260527T010100Z",
    )

    assert result.status == "succeeded"
    assert len(result.steps[0].attempts) == 2
    assert result.steps[0].retry_decisions[0].action == "retry_step"


def test_command_executor_materializes_prompt_only_handoff_artifact(
    tmp_path: Path,
) -> None:
    recipe = _recipe(
        "prompt-artifact",
        (
            CommandStep(
                command=CommandStepCommand.PROMPT_ONLY,
                inline_prompt="Capture this decision.",
                expected_artifacts=("notes/<descriptive-title>.md",),
            ),
        ),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)

    result = CommandExecutor().execute(plan, tmp_path, timestamp="20260527T010200Z")

    assert result.status == "requires_agent_action"
    assert result.steps[0].status == "requires_agent_action"
    artifact_path = (
        tmp_path / "notes" / "prompt-artifact-20260527t010200z-prompt-artifact.md"
    )
    assert artifact_path.exists()
    assert "Capture this decision" in artifact_path.read_text()


def test_autonomy_policy_blocks_plan_blockers(tmp_path: Path) -> None:
    recipe = _recipe(
        "blocked",
        (CommandStep(command=CommandStepCommand.CODEX_EXEC, prompt_file="missing.md"),),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)

    decision = AgentAutonomyPolicy().decide(plan)
    result = CommandExecutor().execute(plan, tmp_path, timestamp="20260527T010300Z")

    assert decision.decision == CommandAutonomyDecisionKind.BLOCK
    assert result.status == "blocked"
    assert result.blocked_reasons


def test_artifact_verifier_reports_missing_and_present_files(tmp_path: Path) -> None:
    verifier = ArtifactVerifier()
    artifact_path = tmp_path / "artifact.md"

    missing = verifier.check(artifact_path)
    artifact_path.write_text("hello")
    present = verifier.check(artifact_path)

    assert missing.exists is False
    assert present.exists is True
    assert present.size_bytes == 5
    assert present.sha256 is not None


def test_agent_policy_allows_recoverable_generated_brief_handoff(
    tmp_path: Path,
) -> None:
    recipe = _recipe(
        "runtime-handoff",
        (
            CommandStep(
                command=CommandStepCommand.OMX_ULTRAGOAL,
                inline_prompt="Create an UltraGoal when the generated brief is ready.",
                brief_file=".agent-remote/runs/runtime-handoff/brief.md",
            ),
        ),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)

    decision = AgentAutonomyPolicy().decide(plan)
    result = CommandExecutor().execute(plan, tmp_path, timestamp="20260527T010400Z")

    assert decision.decision == CommandAutonomyDecisionKind.ALLOW
    assert "recover_generated_prompt_files" in decision.required_safeguards
    assert result.status == "requires_agent_action"
    assert result.steps[0].handoff_path is not None


def test_prompt_handoff_stops_before_following_steps(tmp_path: Path) -> None:
    marker_path = tmp_path / "should-not-run.txt"
    recipe = _recipe(
        "handoff-stop",
        (
            CommandStep(
                command=CommandStepCommand.PROMPT_ONLY,
                inline_prompt="Wait for agent action.",
            ),
            CommandStep(
                command=CommandStepCommand.LOCAL,
                argv=(
                    sys.executable,
                    "-c",
                    f"from pathlib import Path; Path({str(marker_path)!r}).write_text('ran')",
                ),
            ),
        ),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)

    result = CommandExecutor().execute(plan, tmp_path, timestamp="20260527T010500Z")

    assert result.status == "requires_agent_action"
    assert len(result.steps) == 1
    assert not marker_path.exists()


def test_missing_subprocess_artifact_fails_without_materializing(
    tmp_path: Path,
) -> None:
    recipe = _recipe(
        "missing-artifact",
        (
            CommandStep(
                command=CommandStepCommand.LOCAL,
                argv=(sys.executable, "-c", "print('no artifact')"),
                expected_artifacts=("out/report.md",),
            ),
        ),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)

    result = CommandExecutor(max_attempts=1).execute(
        plan,
        tmp_path,
        timestamp="20260527T010600Z",
    )

    assert result.status == "failed"
    assert result.steps[0].failure is not None
    assert result.steps[0].failure.kind == "missing_artifact"
    assert result.steps[0].artifact_checks[0].exists is False
    assert not (tmp_path / "out" / "report.md").exists()


def test_attempt_persistence_redacts_sensitive_argv_and_output(tmp_path: Path) -> None:
    recipe = _recipe(
        "redact",
        (
            CommandStep(
                command=CommandStepCommand.LOCAL,
                argv=(
                    sys.executable,
                    "-c",
                    "import sys; print('token=stdout-secret'); print(sys.argv[-1])",
                    "--token",
                    "argv-secret",
                ),
            ),
        ),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)

    result = CommandExecutor().execute(plan, tmp_path, timestamp="20260527T010700Z")
    attempt = result.steps[0].attempts[0]

    assert result.status == "succeeded"
    assert "argv-secret" not in " ".join(attempt.argv)
    assert "[REDACTED]" in " ".join(attempt.argv)
    assert "stdout-secret" not in Path(attempt.stdout_path).read_text()


def test_redact_text_covers_plain_key_assignments() -> None:
    redacted = redact_text(
        "token=token-secret key=key-secret key: colon-secret "
        '"key": "jsonish secret value" password="foo bar baz" '
        "secret=unquoted secret tail "
        'Authorization: Bearer bearer-secret {"api_key": "super secret value"}'
    )

    assert "token-secret" not in redacted
    assert "key-secret" not in redacted
    assert "colon-secret" not in redacted
    assert "jsonish secret value" not in redacted
    assert "foo bar baz" not in redacted
    assert "unquoted secret tail" not in redacted
    assert "secret tail" not in redacted
    assert "super secret value" not in redacted
    assert "bearer-secret" not in redacted
    assert redacted.count("[REDACTED]") >= 7


def test_actual_run_artifacts_redact_secrets_everywhere(tmp_path: Path) -> None:
    script = """
import sys
print('password="stdout secret value"')
print('token=stdout unquoted tail')
print('{"api_key": "json stdout secret value", "safe": "ok"}')
print('key="stderr secret value"', file=sys.stderr)
print('password=stderr unquoted tail', file=sys.stderr)
raise SystemExit(1)
""".strip()
    recipe = _recipe(
        "redact-all",
        (
            CommandStep(
                command=CommandStepCommand.LOCAL,
                argv=(
                    sys.executable,
                    "-c",
                    script,
                    "--token",
                    "argv secret value",
                    "--header=header secret value",
                    '{"api_key":"json secret value","safe":"ok"}',
                ),
                expected_artifacts=('out/key="handoff secret value".md',),
            ),
        ),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)

    result = CommandExecutor(max_attempts=1).execute(
        plan,
        tmp_path,
        timestamp="20260527T011000Z",
    )

    assert result.status == "failed"
    forbidden = (
        "argv secret value",
        "stdout secret value",
        "stdout unquoted tail",
        "unquoted tail",
        "json stdout secret value",
        "stderr secret value",
        "stderr unquoted tail",
        "header secret value",
        "json secret value",
        "handoff secret value",
    )
    persisted_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path(result.run_dir).rglob("*")
        if path.is_file()
    )
    for secret in forbidden:
        assert secret not in persisted_text
    assert "[REDACTED]" in persisted_text


def test_actual_handoff_redacts_secret_shaped_artifact_paths(tmp_path: Path) -> None:
    recipe = _recipe(
        "handoff-redact",
        (
            CommandStep(
                command=CommandStepCommand.LOCAL,
                argv=(sys.executable, "-c", "print('ok')"),
                expected_artifacts=('out/key="handoff secret value".md',),
            ),
        ),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)

    result = CommandExecutor(max_attempts=1).execute(
        plan,
        tmp_path,
        timestamp="20260527T011100Z",
    )

    assert result.status == "failed"
    handoff_text = Path(result.run_dir, "handoff.md").read_text(encoding="utf-8")
    assert "handoff secret value" not in handoff_text
    assert "[REDACTED]" in handoff_text


def test_actual_run_id_collision_gets_unique_suffix(tmp_path: Path) -> None:
    recipe = _recipe(
        "collision",
        (
            CommandStep(
                command=CommandStepCommand.LOCAL,
                argv=(sys.executable, "-c", "print('ok')"),
            ),
        ),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)

    first = CommandExecutor().execute(plan, tmp_path, timestamp="20260527T010800Z")
    second = CommandExecutor().execute(plan, tmp_path, timestamp="20260527T010800Z")

    assert first.run_id == "20260527T010800Z-collision"
    assert second.run_id == "20260527T010800Z-collision-02"
    assert Path(first.result_path).exists()
    assert Path(second.result_path).exists()


def test_existing_ultragoal_brief_is_policy_gated_handoff(tmp_path: Path) -> None:
    brief_path = tmp_path / "brief.md"
    brief_path.write_text("# Brief\n")
    recipe = _recipe(
        "ultragoal-gated",
        (
            CommandStep(
                command=CommandStepCommand.OMX_ULTRAGOAL,
                brief_file=str(brief_path),
                inline_prompt="Use this brief only after explicit runtime gate.",
            ),
        ),
    )
    plan = build_command_execution_plan(recipe, cwd=tmp_path, dry_run=False)

    result = CommandExecutor().execute(plan, tmp_path, timestamp="20260527T010900Z")

    assert result.status == "requires_agent_action"
    assert result.steps[0].command == "omx_ultragoal"
    assert result.steps[0].attempts == ()
