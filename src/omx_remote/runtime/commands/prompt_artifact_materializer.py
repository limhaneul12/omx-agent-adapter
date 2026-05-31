from pathlib import Path

from omx_remote.runtime.commands.actual_run_record_writer import ActualRunPaths
from omx_remote.runtime.commands.command_artifact_path_policy import (
    validate_materialized_artifact_paths,
)
from omx_remote.runtime.commands.command_output_redaction import redact_text
from omx_remote.runtime.commands.command_placeholder_resolution import (
    ExecutionPlaceholderState,
    resolve_artifact_path,
)
from omx_remote.schemas.commands.command_recipe_schemas import CommandPlanStep


def render_prompt_artifact(
    path: Path,
    step: CommandPlanStep,
    state: ExecutionPlaceholderState,
) -> str:
    """Render content for a prompt-only or runtime handoff artifact.

    Args:
        path: See function signature.
        step: See function signature.
        state: See function signature.

    Returns:
        See function return annotation."""
    raw_prompt_text: str = step.inline_prompt or "Command step handoff artifact."
    prompt_text: str = redact_text(raw_prompt_text)
    if path.name == "SKILL.md":
        content = (
            "---\n"
            f"name: {state.skill_name}\n"
            "description: Generated command workflow skill artifact.\n"
            "---\n\n"
            f"# {state.skill_name}\n\n"
            f"Generated from `{state.command_id}` run `{state.run_id}`.\n\n"
            "## Handoff\n\n"
            f"{prompt_text}\n"
        )
        return content
    if path.name == "openai.yaml":
        content = (
            "interface:\n"
            f'  display_name: "{state.skill_name}"\n'
            '  short_description: "Generated command workflow skill"\n'
            f'  default_prompt: "Use ${state.skill_name} for this workflow."\n'
        )
        return content
    if str(path).startswith("/Users/imhaneul/Desktop/Alexandria"):
        title = path.stem
        content = (
            "---\n"
            "alexandria_type: context\n"
            f"title: {title}\n"
            "project: omx-agent-adapter\n"
            "source: omx-agent-adapter\n"
            "status: active\n"
            "---\n\n"
            f"# {title}\n\n"
            f"- command: `{state.command_id}`\n"
            f"- run: `{state.run_id}`\n"
            "- secret policy: summaries and artifact paths only; no secrets stored.\n\n"
            "## Captured handoff\n\n"
            f"{prompt_text}\n"
        )
        return content
    content = (
        f"# {path.stem}\n\n"
        f"- command: `{state.command_id}`\n"
        f"- run: `{state.run_id}`\n\n"
        "## Handoff\n\n"
        f"{prompt_text}\n"
    )
    return content


def materialize_expected_artifacts(
    step: CommandPlanStep,
    paths: ActualRunPaths,
    state: ExecutionPlaceholderState,
    cwd: str | Path,
) -> tuple[Path, ...]:
    """Create concrete handoff artifacts for declared expected paths.

    Args:
        step: See function signature.
        paths: See function signature.
        state: See function signature.
        cwd: See function signature.

    Returns:
        See function return annotation."""
    artifact_paths: tuple[Path, ...] = validate_materialized_artifact_paths(
        (
            resolve_artifact_path(artifact, state)
            for artifact in step.expected_artifacts
        ),
        cwd,
    )
    materialized_paths: list[Path] = []
    for artifact_path in artifact_paths:
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        if not artifact_path.exists():
            artifact_path.write_text(
                render_prompt_artifact(artifact_path, step, state),
                encoding="utf-8",
            )
        materialized_paths.append(artifact_path)
    if not step.expected_artifacts:
        handoff_path = paths.run_dir / "steps" / f"{step.index:03d}" / "handoff.md"
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(
            render_prompt_artifact(handoff_path, step, state),
            encoding="utf-8",
        )
        materialized_paths.append(handoff_path)
    return tuple(materialized_paths)
