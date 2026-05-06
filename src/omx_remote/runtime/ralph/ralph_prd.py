from pathlib import Path

from pydantic import ValidationError

from omx_remote.runtime.ralph.ralph_state import read_json_object
from omx_remote.schemas.ralph.prd_schemas import RalphPrdArtifact


def summarize_prd_validation_error(validation_error: ValidationError) -> str:
    """Summarizes invalid typed Ralph PRD fields from a Pydantic error.

    Args:
        validation_error [ValidationError]: Validation error raised while parsing `.omx/prd.json`.

    Returns:
        str: Human-readable invalid field summary.
    """
    field_paths: list[str] = []

    for error_payload in validation_error.errors():
        raw_location: object = error_payload.get("loc")
        if not isinstance(raw_location, tuple):
            continue

        location_parts: list[str] = [str(location_token) for location_token in raw_location]
        if not location_parts:
            continue

        field_paths.append(".".join(location_parts))

    if not field_paths:
        invalid_field_summary: str = "typed Ralph PRD fields"
        return invalid_field_summary

    invalid_field_summary = ", ".join(field_paths)
    return invalid_field_summary


def read_ralph_prd_artifact(prd_path: Path) -> RalphPrdArtifact:
    """Reads and validates a typed Ralph PRD artifact.

    Args:
        prd_path [Path]: Path to `.omx/prd.json`.

    Returns:
        RalphPrdArtifact: Typed Ralph PRD artifact.

    Raises:
        ValueError: Raised when the PRD artifact is missing, unreadable, or invalid.
    """
    prd_payload: dict[str, object] | None = read_json_object(prd_path)
    if prd_payload is None:
        raise ValueError("Invalid or unreadable .omx/prd.json: expected JSON object.")

    try:
        artifact: RalphPrdArtifact = RalphPrdArtifact.model_validate(prd_payload)
    except ValidationError as validation_error:
        invalid_fields: str = summarize_prd_validation_error(validation_error)
        raise ValueError(
            "Invalid .omx/prd.json: expected a typed Ralph PRD artifact with fields "
            f"{invalid_fields}."
        ) from validation_error

    return artifact


def normalize_objective_text(objective_text: str) -> str:
    """Normalizes objective text for equality checks.

    Args:
        objective_text [str]: Raw objective/task text.

    Returns:
        str: Lowercase stripped objective text.
    """
    normalized_objective_text: str = objective_text.strip().lower()
    return normalized_objective_text


def resolve_ralph_launch_task_from_prd(
    task: str,
    ralph_prd_artifact: RalphPrdArtifact,
) -> str:
    """Resolves the canonical Ralph launch task from a validated PRD artifact.

    Args:
        task [str]: CLI task text requested for Ralph launch.
        ralph_prd_artifact [RalphPrdArtifact]: Typed Ralph PRD artifact.

    Returns:
        str: Canonical PRD objective text used for launch.

    Raises:
        ValueError: Raised when CLI task text does not match the typed PRD objective.
    """
    normalized_task_text: str = normalize_objective_text(task)
    normalized_prd_objective_text: str = normalize_objective_text(
        ralph_prd_artifact.objective
    )
    if normalized_task_text != normalized_prd_objective_text:
        raise ValueError(
            "Launch task text must match the typed Ralph PRD objective in .omx/prd.json before execution proceeds."
        )

    canonical_launch_task: str = ralph_prd_artifact.objective.strip()
    return canonical_launch_task


def resolve_ralph_team_launch_task_from_prd(
    ralph_prd_artifact: RalphPrdArtifact,
) -> tuple[str, int]:
    """Resolves the canonical Team launch task/count from a typed Ralph PRD artifact.

    Args:
        ralph_prd_artifact [RalphPrdArtifact]: Typed Ralph PRD artifact.

    Returns:
        tuple[str, int]: Canonical launch task and requested Team worker count.

    Raises:
        ValueError: Raised when required Team fanout fields are missing.
    """
    if not ralph_prd_artifact.requires_team_fanout:
        raise ValueError(
            "The typed Ralph PRD artifact does not request Team fanout, so Team launch cannot proceed."
        )

    team_worker_count: int | None = ralph_prd_artifact.team_worker_count
    if team_worker_count is None:
        raise ValueError(
            "The typed Ralph PRD artifact requires Team fanout but does not declare team_worker_count."
        )

    if ralph_prd_artifact.team_worker_assignments is None:
        raise ValueError(
            "The typed Ralph PRD artifact requires Team fanout but does not declare Team worker assignments."
        )

    canonical_launch_task: str = ralph_prd_artifact.objective.strip()
    return canonical_launch_task, team_worker_count


def validate_ralph_prd_gate() -> RalphPrdArtifact:
    """Validates the workspace Ralph PRD gate before launch.

    Returns:
        RalphPrdArtifact: Typed Ralph PRD artifact loaded from `.omx/prd.json`.

    Raises:
        ValueError: Raised when `.omx/prd.json` is absent or invalid.
    """
    prd_path: Path = Path.cwd() / ".omx" / "prd.json"
    if not prd_path.exists():
        raise ValueError(
            "Missing required PRD.json at .omx/prd.json. Create the file before running `agent-remote ralph launch`."
        )

    artifact: RalphPrdArtifact = read_ralph_prd_artifact(prd_path)
    return artifact


def validate_ralph_launch_task(task: str) -> str:
    """Normalizes and validates task text for Ralph launch.

    Args:
        task [str]: Raw task text from the CLI.

    Returns:
        str: Stripped non-blank task text.

    Raises:
        ValueError: If the task text is blank after stripping.
    """
    normalized_task: str = task.strip()
    if normalized_task == "":
        raise ValueError("Task text must not be blank.")

    return normalized_task
