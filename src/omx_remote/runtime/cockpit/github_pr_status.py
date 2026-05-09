from __future__ import annotations

import asyncio
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request

import orjson

from omx_remote.adapter_types.json_types import JsonArray, JsonObject, JsonValue
from omx_remote.schemas.cockpit.snapshot_schemas import CockpitPullRequestObservation

GITHUB_API_ROOT = "https://api.github.com"
CODEX_NO_MAJOR_ISSUES_MARKER = "didn't find any major issues"


def _run_git_command(repo_root: str, arguments: tuple[str, ...]) -> str | None:
    """Run one git command and normalize stdout.

    Args:
        repo_root [str]: Repository root used as the git working directory.
        arguments [tuple[str, ...]]: Git arguments without the executable name.

    Returns:
        str | None: Stripped stdout when the command succeeds with content, otherwise None.
    """
    command_arguments: list[str] = ["git", *arguments]
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


def _read_git_credential_token(repo_root: str) -> str | None:
    """Read a GitHub credential token without logging or persisting it.

    Args:
        repo_root [str]: Repository root used for git credential lookup.

    Returns:
        str | None: Credential password/token when available, otherwise None.
    """
    try:
        completed_process: subprocess.CompletedProcess[str] = subprocess.run(
            ["git", "credential", "fill"],
            cwd=repo_root,
            input="protocol=https\nhost=github.com\n\n",
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
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


def _read_github_api_json(repo_root: str, api_path: str) -> JsonValue | None:
    """Read one GitHub REST API JSON response.

    Args:
        repo_root [str]: Repository root used for token lookup.
        api_path [str]: API path beginning with `/repos/...`.

    Returns:
        JsonValue | None: Parsed JSON payload when the request succeeds, otherwise None.
    """
    token: str | None = _read_github_token(repo_root)
    if token is None:
        missing_payload: JsonValue | None = None
        return missing_payload

    request = urllib.request.Request(
        f"{GITHUB_API_ROOT}{api_path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "agent-remote-cockpit",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            response_body: bytes = response.read()
    except (OSError, urllib.error.HTTPError, urllib.error.URLError):
        failed_payload: JsonValue | None = None
        return failed_payload

    try:
        parsed_payload = orjson.loads(response_body)
    except orjson.JSONDecodeError:
        malformed_payload: JsonValue | None = None
        return malformed_payload

    payload: JsonValue | None = parsed_payload
    return payload


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


def _as_json_object(raw_value: JsonValue | None) -> JsonObject | None:
    """Narrow a JSON value to an object.

    Args:
        raw_value [JsonValue | None]: Raw JSON value.

    Returns:
        JsonObject | None: The object value when present, otherwise None.
    """
    if isinstance(raw_value, dict):
        object_value: JsonObject | None = raw_value
        return object_value

    missing_object: JsonObject | None = None
    return missing_object


def _as_json_array(raw_value: JsonValue | None) -> JsonArray | None:
    """Narrow a JSON value to an array.

    Args:
        raw_value [JsonValue | None]: Raw JSON value.

    Returns:
        JsonArray | None: The array value when present, otherwise None.
    """
    if isinstance(raw_value, list):
        array_value: JsonArray | None = raw_value
        return array_value

    missing_array: JsonArray | None = None
    return missing_array


def _as_non_empty_text(raw_value: JsonValue | None) -> str | None:
    """Narrow a JSON value to non-empty text.

    Args:
        raw_value [JsonValue | None]: Raw JSON value.

    Returns:
        str | None: Non-empty string when available, otherwise None.
    """
    if not isinstance(raw_value, str):
        missing_text: str | None = None
        return missing_text

    if raw_value == "":
        empty_text: str | None = None
        return empty_text

    text_value: str | None = raw_value
    return text_value


def _as_positive_int(raw_value: JsonValue | None) -> int | None:
    """Narrow a JSON value to a positive integer.

    Args:
        raw_value [JsonValue | None]: Raw JSON value.

    Returns:
        int | None: Positive integer when available, otherwise None.
    """
    if not isinstance(raw_value, int):
        missing_int: int | None = None
        return missing_int

    if raw_value < 1:
        invalid_int: int | None = None
        return invalid_int

    int_value: int | None = raw_value
    return int_value


def _first_open_pull_request(pulls_payload: JsonValue | None) -> JsonObject | None:
    """Select the first object from an open pull-request API payload.

    Args:
        pulls_payload [JsonValue | None]: Raw pulls list payload.

    Returns:
        JsonObject | None: First pull request object when available.
    """
    pulls_array: JsonArray | None = _as_json_array(pulls_payload)
    if pulls_array is None:
        missing_pull: JsonObject | None = None
        return missing_pull

    for pull_value in pulls_array:
        pull_object: JsonObject | None = _as_json_object(pull_value)
        if pull_object is not None:
            selected_pull: JsonObject | None = pull_object
            return selected_pull

    no_pull: JsonObject | None = None
    return no_pull


def _head_sha_from_pull(pull_request: JsonObject) -> str | None:
    """Extract the head SHA from a pull-request payload.

    Args:
        pull_request [JsonObject]: Pull-request object payload.

    Returns:
        str | None: Head SHA when present.
    """
    head_value: JsonValue | None = pull_request.get("head")
    head_object: JsonObject | None = _as_json_object(head_value)
    if head_object is None:
        missing_sha: str | None = None
        return missing_sha

    sha_text: str | None = _as_non_empty_text(head_object.get("sha"))
    return sha_text


def _classify_review_state(reviews_payload: JsonValue | None, comments_payload: JsonValue | None) -> str:
    """Classify review state from GitHub reviews and Codex issue comments.

    Args:
        reviews_payload [JsonValue | None]: Pull request reviews API payload.
        comments_payload [JsonValue | None]: Issue comments API payload.

    Returns:
        str: Normalized review state summary.
    """
    reviews_array: JsonArray | None = _as_json_array(reviews_payload)
    saw_approved_review: bool = False
    if reviews_array is not None:
        for review_value in reviews_array:
            review_object: JsonObject | None = _as_json_object(review_value)
            if review_object is None:
                continue
            state_text: str | None = _as_non_empty_text(review_object.get("state"))
            if state_text is None:
                continue
            normalized_state: str = state_text.lower()
            if normalized_state == "changes_requested":
                changes_requested_state: str = "changes_requested"
                return changes_requested_state
            if normalized_state == "approved":
                saw_approved_review = True

    comments_array: JsonArray | None = _as_json_array(comments_payload)
    if comments_array is not None:
        for comment_value in comments_array:
            comment_object: JsonObject | None = _as_json_object(comment_value)
            if comment_object is None:
                continue
            body_text: str | None = _as_non_empty_text(comment_object.get("body"))
            if body_text is None:
                continue
            if CODEX_NO_MAJOR_ISSUES_MARKER in body_text.lower():
                codex_state: str = "codex_no_major_issues"
                return codex_state

    if saw_approved_review:
        approved_state: str = "approved"
        return approved_state

    if reviews_array is None:
        unknown_state: str = "unknown"
        return unknown_state

    pending_state: str = "pending_or_unreviewed"
    return pending_state


def _classify_check_runs(check_runs_payload: JsonValue | None) -> str:
    """Classify GitHub check-runs state.

    Args:
        check_runs_payload [JsonValue | None]: Check-runs API payload.

    Returns:
        str: Normalized check-runs state.
    """
    check_runs_object: JsonObject | None = _as_json_object(check_runs_payload)
    if check_runs_object is None:
        unknown_state: str = "unknown"
        return unknown_state

    runs_array: JsonArray | None = _as_json_array(check_runs_object.get("check_runs"))
    if runs_array is None or len(runs_array) == 0:
        no_runs_state: str = "no_check_runs"
        return no_runs_state

    saw_success_like_run: bool = False
    for run_value in runs_array:
        run_object: JsonObject | None = _as_json_object(run_value)
        if run_object is None:
            continue
        status_text: str | None = _as_non_empty_text(run_object.get("status"))
        conclusion_text: str | None = _as_non_empty_text(run_object.get("conclusion"))
        if status_text != "completed":
            pending_state: str = "pending"
            return pending_state
        if conclusion_text in {"failure", "timed_out", "cancelled", "action_required"}:
            failure_state: str = "failure"
            return failure_state
        if conclusion_text in {"success", "skipped", "neutral"}:
            saw_success_like_run = True

    if saw_success_like_run:
        success_state: str = "success"
        return success_state

    unknown_state = "unknown"
    return unknown_state


def _classify_check_state(status_payload: JsonValue | None, check_runs_payload: JsonValue | None) -> str:
    """Classify combined GitHub commit status and check-runs state.

    Args:
        status_payload [JsonValue | None]: Combined status API payload.
        check_runs_payload [JsonValue | None]: Check-runs API payload.

    Returns:
        str: Normalized check state.
    """
    status_object: JsonObject | None = _as_json_object(status_payload)
    status_state: str | None = None
    if status_object is not None:
        status_state = _as_non_empty_text(status_object.get("state"))

    check_runs_state: str = _classify_check_runs(check_runs_payload)
    if status_state in {"failure", "error"} or check_runs_state == "failure":
        failed_state: str = "failure"
        return failed_state
    if status_state == "pending" or check_runs_state == "pending":
        pending_state: str = "pending"
        return pending_state
    if status_state == "success" or check_runs_state == "success":
        success_state: str = "success"
        return success_state
    if check_runs_state == "no_check_runs" and status_state is None:
        no_checks_state: str = "no_checks"
        return no_checks_state
    if status_state is not None:
        observed_status_state: str = status_state
        return observed_status_state

    unknown_state: str = "unknown"
    return unknown_state


def _build_pull_request_query_path(owner: str, repo: str, branch: str) -> str:
    """Build the open pull request query path for one branch.

    Args:
        owner [str]: GitHub repository owner.
        repo [str]: GitHub repository name.
        branch [str]: Current branch name.

    Returns:
        str: GitHub REST API path and query string.
    """
    encoded_head: str = urllib.parse.quote(f"{owner}:{branch}", safe=":/")
    path: str = f"/repos/{owner}/{repo}/pulls?head={encoded_head}&state=open"
    return path


def _build_observation_detail(
    pull_request_number: int,
    mergeable_state: str,
    review_state: str,
    check_state: str,
) -> str:
    """Build a concise PR status detail string.

    Args:
        pull_request_number [int]: Pull request number.
        mergeable_state [str]: GitHub mergeable state text.
        review_state [str]: Normalized review state.
        check_state [str]: Normalized check state.

    Returns:
        str: Human-readable status detail.
    """
    detail: str = (
        f"PR #{pull_request_number} is open; mergeable_state={mergeable_state}; "
        f"review_state={review_state}; check_state={check_state}."
    )
    return detail


def _read_pull_request_status_sync(repo_root: str) -> CockpitPullRequestObservation:
    """Read GitHub PR status synchronously.

    Args:
        repo_root [str]: Repository root whose current branch should be inspected.

    Returns:
        CockpitPullRequestObservation: Read-only PR status evidence.
    """
    remote_url: str | None = _run_git_command(repo_root, ("remote", "get-url", "origin"))
    if remote_url is None:
        observation = CockpitPullRequestObservation(
            provider="github",
            branch="unknown",
            status="unavailable",
            pull_request_number=None,
            mergeable_state=None,
            review_state="unknown",
            check_state="unknown",
            detail="GitHub PR status unavailable: origin remote could not be read.",
            url=None,
            warnings=("origin remote could not be read",),
        )
        return observation

    owner_repo: tuple[str, str] | None = _parse_github_owner_repo(remote_url)
    if owner_repo is None:
        observation = CockpitPullRequestObservation(
            provider="github",
            branch="unknown",
            status="unavailable",
            pull_request_number=None,
            mergeable_state=None,
            review_state="unknown",
            check_state="unknown",
            detail="GitHub PR status unavailable: origin remote is not a GitHub URL.",
            url=None,
            warnings=("origin remote is not a GitHub URL",),
        )
        return observation

    branch: str | None = _run_git_command(repo_root, ("branch", "--show-current"))
    if branch is None:
        observation = CockpitPullRequestObservation(
            provider="github",
            branch="unknown",
            status="unavailable",
            pull_request_number=None,
            mergeable_state=None,
            review_state="unknown",
            check_state="unknown",
            detail="GitHub PR status unavailable: current branch could not be read.",
            url=None,
            warnings=("current branch could not be read",),
        )
        return observation

    owner, repo = owner_repo
    pulls_path: str = _build_pull_request_query_path(owner, repo, branch)
    pulls_payload: JsonValue | None = _read_github_api_json(repo_root, pulls_path)
    if pulls_payload is None:
        observation = CockpitPullRequestObservation(
            provider="github",
            branch=branch,
            status="unavailable",
            pull_request_number=None,
            mergeable_state=None,
            review_state="unknown",
            check_state="unknown",
            detail=f"GitHub PR status unavailable: open pull request query failed for branch {branch}.",
            url=None,
            warnings=("open pull request query failed",),
        )
        return observation

    pull_request: JsonObject | None = _first_open_pull_request(pulls_payload)
    if pull_request is None:
        observation = CockpitPullRequestObservation(
            provider="github",
            branch=branch,
            status="no_open_pull_request",
            pull_request_number=None,
            mergeable_state=None,
            review_state="not_applicable",
            check_state="not_applicable",
            detail=f"No open GitHub pull request found for branch {branch}.",
            url=None,
        )
        return observation

    pull_request_number: int | None = _as_positive_int(pull_request.get("number"))
    pull_request_url: str | None = _as_non_empty_text(pull_request.get("html_url"))
    pull_request_state: str | None = _as_non_empty_text(pull_request.get("state"))
    mergeable_state: str | None = _as_non_empty_text(pull_request.get("mergeable_state"))
    head_sha: str | None = _head_sha_from_pull(pull_request)
    if pull_request_number is None or pull_request_state is None or head_sha is None:
        observation = CockpitPullRequestObservation(
            provider="github",
            branch=branch,
            status="unavailable",
            pull_request_number=pull_request_number,
            mergeable_state=mergeable_state,
            review_state="unknown",
            check_state="unknown",
            detail=f"GitHub PR status unavailable: malformed pull request payload for branch {branch}.",
            url=pull_request_url,
            warnings=("malformed pull request payload",),
        )
        return observation

    normalized_mergeable_state: str = "unknown"
    if mergeable_state is not None:
        normalized_mergeable_state = mergeable_state

    reviews_payload: JsonValue | None = _read_github_api_json(
        repo_root,
        f"/repos/{owner}/{repo}/pulls/{pull_request_number}/reviews",
    )
    comments_payload: JsonValue | None = _read_github_api_json(
        repo_root,
        f"/repos/{owner}/{repo}/issues/{pull_request_number}/comments",
    )
    status_payload: JsonValue | None = _read_github_api_json(
        repo_root,
        f"/repos/{owner}/{repo}/commits/{head_sha}/status",
    )
    check_runs_payload: JsonValue | None = _read_github_api_json(
        repo_root,
        f"/repos/{owner}/{repo}/commits/{head_sha}/check-runs",
    )
    review_state: str = _classify_review_state(reviews_payload, comments_payload)
    check_state: str = _classify_check_state(status_payload, check_runs_payload)
    detail: str = _build_observation_detail(
        pull_request_number=pull_request_number,
        mergeable_state=normalized_mergeable_state,
        review_state=review_state,
        check_state=check_state,
    )
    observation = CockpitPullRequestObservation(
        provider="github",
        branch=branch,
        status=pull_request_state,
        pull_request_number=pull_request_number,
        mergeable_state=normalized_mergeable_state,
        review_state=review_state,
        check_state=check_state,
        detail=detail,
        url=pull_request_url,
    )
    return observation


async def read_github_pull_request_status(repo_root: str) -> CockpitPullRequestObservation:
    """Read optional GitHub PR/review/check evidence for a repo.

    Args:
        repo_root [str]: Repository root whose current branch should be inspected.

    Returns:
        CockpitPullRequestObservation: Read-only PR status evidence, or unavailable evidence.
    """
    observation: CockpitPullRequestObservation = await asyncio.to_thread(
        _read_pull_request_status_sync,
        repo_root,
    )
    return observation
