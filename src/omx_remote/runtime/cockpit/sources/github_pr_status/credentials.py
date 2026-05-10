"""Credential helpers for GitHub PR cockpit evidence."""

from __future__ import annotations

import os
import subprocess

from omx_remote.runtime.cockpit.sources.github_pr_status.git_repo import (
    _parse_github_owner_repo,
    _run_git_command,
)

GITHUB_CREDENTIAL_TIMEOUT_SECONDS = 5


def _build_noninteractive_git_env() -> dict[str, str]:
    """Build a git environment that forbids credential prompts.

    Returns:
        dict[str, str]: Environment variables for non-interactive git commands.
    """
    git_env: dict[str, str] = os.environ.copy()
    git_env["GIT_TERMINAL_PROMPT"] = "0"
    git_env["GCM_INTERACTIVE"] = "never"
    return git_env


def _build_git_credential_fill_input(repo_root: str) -> str:
    """Build the credential lookup request for GitHub credentials.

    Args:
        repo_root [str]: Repository root used to read the origin remote.

    Returns:
        str: Credential description passed to `git credential fill`.
    """
    credential_lines: list[str] = ["protocol=https", "host=github.com"]
    remote_url: str | None = _run_git_command(
        repo_root, ("remote", "get-url", "origin")
    )
    if remote_url is not None:
        owner_repo: tuple[str, str] | None = _parse_github_owner_repo(remote_url)
        if owner_repo is not None:
            owner, repo = owner_repo
            credential_lines.append(f"path={owner}/{repo}.git")

    credential_query: str = "\n".join(credential_lines) + "\n\n"
    return credential_query


def _read_git_credential_token(repo_root: str) -> str | None:
    """Read a GitHub credential token without logging or persisting it.

    Args:
        repo_root [str]: Repository root used for git credential lookup.

    Returns:
        str | None: Credential password/token when available, otherwise None.
    """
    credential_env: dict[str, str] = _build_noninteractive_git_env()
    credential_input: str = _build_git_credential_fill_input(repo_root)
    try:
        completed_process: subprocess.CompletedProcess[str] = subprocess.run(
            ["git", "credential", "fill"],
            cwd=repo_root,
            input=credential_input,
            text=True,
            capture_output=True,
            check=False,
            env=credential_env,
            timeout=GITHUB_CREDENTIAL_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        missing_token: str | None = None
        return missing_token

    if completed_process.returncode != 0:
        failed_token: str | None = None
        return failed_token

    for credential_line in completed_process.stdout.splitlines():
        if credential_line.startswith("password="):
            credential_token = credential_line.removeprefix("password=").strip()
            if credential_token != "":
                token: str | None = credential_token
                return token

    missing_password: str | None = None
    return missing_password


def _read_github_token(repo_root: str) -> str | None:
    """Find a GitHub API token from environment or git credential storage.

    Args:
        repo_root [str]: Repository root used for git credential lookup.

    Returns:
        str | None: Token when available, otherwise None.
    """
    env_token: str | None = os.environ.get("GITHUB_TOKEN")
    if env_token is not None and env_token.strip() != "":
        token: str | None = env_token.strip()
        return token

    gh_token: str | None = os.environ.get("GH_TOKEN")
    if gh_token is not None and gh_token.strip() != "":
        token = gh_token.strip()
        return token

    credential_token: str | None = _read_git_credential_token(repo_root)
    return credential_token
