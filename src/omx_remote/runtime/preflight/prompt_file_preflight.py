from pathlib import Path

from omx_remote.schemas.preflight_schemas import (
    PreflightCategory,
    PreflightCheckResult,
    PreflightSeverity,
)


def _resolve_prompt_path(cwd: str | Path, prompt_path: str | Path) -> Path:
    """Resolve a prompt path against a working directory.

    Args:
        cwd [str | Path]: Working directory.
        prompt_path [str | Path]: Prompt path to resolve.

    Returns:
        Path: Resolved prompt path.
    """
    candidate_path = Path(prompt_path)
    if candidate_path.is_absolute():
        resolved_path: Path = candidate_path
        return resolved_path

    resolved_path = Path(cwd) / candidate_path
    return resolved_path


def check_prompt_file(
    cwd: str | Path,
    prompt_path: str | Path,
    allow_outside_cwd: bool = False,
) -> PreflightCheckResult:
    """Check prompt file existence and workspace visibility.

    Args:
        cwd [str | Path]: Working directory that should contain the prompt.
        prompt_path [str | Path]: Prompt path to inspect.
        allow_outside_cwd [bool]: Whether adapter-owned absolute prompts may live
            outside the target working directory.

    Returns:
        PreflightCheckResult: Prompt-file preflight result.
    """
    root_path: Path = Path(cwd).resolve()
    resolved_prompt_path: Path = _resolve_prompt_path(root_path, prompt_path).resolve()
    prompt_exists: bool = resolved_prompt_path.exists()
    try:
        resolved_prompt_path.relative_to(root_path)
    except ValueError:
        if allow_outside_cwd and prompt_exists:
            allowed_outside_result = PreflightCheckResult(
                category=PreflightCategory.PROMPT_FILE_VISIBILITY,
                severity=PreflightSeverity.INFO,
                summary="adapter-owned prompt file is visible",
                detail=(
                    f"{resolved_prompt_path} exists outside {root_path} as an "
                    "adapter-owned builtin prompt."
                ),
                blocks_execution=False,
                evidence=str(resolved_prompt_path),
            )
            return allowed_outside_result
        outside_result = PreflightCheckResult(
            category=PreflightCategory.PROMPT_FILE_VISIBILITY,
            severity=PreflightSeverity.BLOCKER,
            summary="prompt file is outside the working directory",
            detail=f"{resolved_prompt_path} is outside {root_path}.",
            blocks_execution=True,
            evidence=str(resolved_prompt_path),
        )
        return outside_result

    if not prompt_exists:
        missing_result = PreflightCheckResult(
            category=PreflightCategory.PROMPT_FILE_VISIBILITY,
            severity=PreflightSeverity.BLOCKER,
            summary="prompt file does not exist",
            detail=f"{resolved_prompt_path} was not found.",
            blocks_execution=True,
            evidence=str(resolved_prompt_path),
        )
        return missing_result

    visible_result = PreflightCheckResult(
        category=PreflightCategory.PROMPT_FILE_VISIBILITY,
        severity=PreflightSeverity.INFO,
        summary="prompt file is visible",
        detail=f"{resolved_prompt_path} exists inside {root_path}.",
        blocks_execution=False,
        evidence=str(resolved_prompt_path),
    )
    return visible_result
