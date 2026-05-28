from pathlib import Path
from shlex import quote as quote_shell_token

from typer.testing import CliRunner

from omx_remote.cli import app
from omx_remote.cli_launcher import next_cli
from omx_remote.schemas.next.next_action_schemas import NextActionResult


def test_next_cli_outputs_read_only_json(monkeypatch, tmp_path: Path) -> None:
    async def fake_read_next_action(request):
        assert request.repo_root == str(tmp_path.resolve())
        assert request.task == "verify current repo state"
        assert request.team_names == ("alpha-team",)
        return NextActionResult(
            recommended_action="inspect_route_recommendation",
            safe_to_mutate=True,
            requires_review=False,
            summary="Next action is read-only.",
            why=("No blocking evidence was found.",),
            source_names=("runtime_status", "route_policy"),
            recommended_commands=(
                (
                    "agent-remote cockpit snapshot "
                    f"--cwd {quote_shell_token(str(tmp_path.resolve()))} --json"
                ),
            ),
            blocked_actions=(),
            route_recommendations=(),
            warnings=(),
        )

    monkeypatch.setattr(next_cli, "read_next_action", fake_read_next_action)

    result = CliRunner().invoke(
        app,
        [
            "next",
            "--cwd",
            str(tmp_path),
            "--task",
            "verify current repo state",
            "--team",
            "alpha-team",
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"recommended_action": "inspect_route_recommendation"' in result.stdout
    assert '"safe_to_mutate": true' in result.stdout


def test_next_cli_human_output_does_not_execute_mutation(monkeypatch, tmp_path: Path) -> None:
    async def fake_read_next_action(request):
        assert request.repo_root == str(tmp_path.resolve())
        return NextActionResult(
            recommended_action="observe",
            safe_to_mutate=True,
            requires_review=False,
            summary="No blocking evidence was found.",
            why=("Cockpit found no active runtime.",),
            source_names=("runtime_status",),
            recommended_commands=(
                (
                    "agent-remote cockpit snapshot "
                    f"--cwd {quote_shell_token(str(tmp_path.resolve()))} --json"
                ),
            ),
            blocked_actions=(),
            route_recommendations=(),
            warnings=(),
        )

    monkeypatch.setattr(next_cli, "read_next_action", fake_read_next_action)

    result = CliRunner().invoke(app, ["next", "--cwd", str(tmp_path)])

    assert result.exit_code == 0
    assert "recommended_action: observe" in result.stdout
    assert "agent-remote cockpit snapshot" in result.stdout
