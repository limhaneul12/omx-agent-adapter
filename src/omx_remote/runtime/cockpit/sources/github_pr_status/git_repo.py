"""Git repository helpers for GitHub PR cockpit evidence."""

from __future__ import annotations

import subprocess


def _run_git_command(repo_root: str, arguments: tuple[str, ...]) -> str | None:
    """Run one git command and normalize stdout.

    Args:
        repo_root [str]: Repository root used as the git working directory.
        arguments [tuple[str, ...]]: Git arguments without the executable name.

    Returns:
        str | None: Stripped stdout when the command succeeds with content, otherwise None.
    """
    command_arguments: tuple[str, ...] = ("git", *arguments)
    try:
        completed_process: subprocess.CompletedProcess[str] = subprocess.run(
            command_arguments,
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        missing_output: str | None = None
        return missing_output

    if completed_process.returncode != 0:
        failed_output: str | None = None
        return failed_output

    stripped_output: str = completed_process.stdout.strip()
    if stripped_output == "":
        empty_output: str | None = None
        return empty_output

    command_output: str | None = stripped_output
    return command_output


def _parse_github_owner_repo(remote_url: str) -> tuple[str, str] | None:
    """Parse a GitHub owner/repo pair from a git remote URL.

    Args:
        remote_url [str]: Git remote URL from `git remote get-url origin`.

    Returns:
        tuple[str, str] | None: Owner/repo pair when the URL targets GitHub.
    """
    normalized_remote: str = remote_url.strip()
    if normalized_remote.endswith(".git"):
        normalized_remote = normalized_remote[:-4]

    marker: str = "github.com/"
    if marker in normalized_remote:
        _, owner_repo_text = normalized_remote.rsplit(marker, 1)
    elif normalized_remote.startswith("git@github.com:"):
        owner_repo_text = normalized_remote.removeprefix("git@github.com:")
    else:
        missing_owner_repo: tuple[str, str] | None = None
        return missing_owner_repo

    owner_repo_parts: list[str] = owner_repo_text.split("/")
    if len(owner_repo_parts) != 2:
        invalid_owner_repo: tuple[str, str] | None = None
        return invalid_owner_repo

    owner_text, repo_text = owner_repo_parts
    if owner_text == "" or repo_text == "":
        empty_owner_repo: tuple[str, str] | None = None
        return empty_owner_repo

    owner_repo: tuple[str, str] | None = (owner_text, repo_text)
    return owner_repo
