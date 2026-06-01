"""Shared per-call context helpers for omx-agent MCP tools."""

from pathlib import Path


def effective_cwd(default_cwd: Path, cwd: str | None) -> str:
    """Resolve per-call cwd override text.

    Args:
        default_cwd [Path]: Server default working directory.
        cwd [str | None]: Per-tool override.

    Returns:
        str: Effective cwd text.
    """
    if cwd is None:
        cwd_text = str(default_cwd)
        return cwd_text
    cwd_text = cwd
    return cwd_text


def effective_config_path(
    default_config_path: Path | None,
    config_path: str | None,
) -> str | None:
    """Resolve per-call config override text.

    Args:
        default_config_path [Path | None]: Server default config path.
        config_path [str | None]: Per-tool override.

    Returns:
        str | None: Effective config path text.
    """
    if config_path is not None:
        config_text: str | None = config_path
        return config_text
    if default_config_path is None:
        missing_config: None = None
        return missing_config
    config_text = str(default_config_path)
    return config_text
