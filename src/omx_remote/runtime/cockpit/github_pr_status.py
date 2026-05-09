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
CODEX_REVIEW_BOT_LOGIN = "chatgpt-codex-connector[bot]"
GITHUB_API_PAGE_SIZE = 100
GITHUB_CREDENTIAL_TIMEOUT_SECONDS = 5


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


def _build_paginated_array_path(api_path: str, page_number: int) -> str:
    """Build a GitHub API path with explicit array pagination.

    Args:
        api_path [str]: Base API path to read.
        page_number [int]: One-indexed page number to request.

    Returns:
        str: API path with `per_page` and `page` query parameters.
    """
    separator: str = "?"
    if "?" in api_path:
        separator = "&"

    paginated_path: str = (
        f"{api_path}{separator}per_page={GITHUB_API_PAGE_SIZE}&page={page_number}"
    )
    return paginated_path


def _read_github_paginated_array_json(
    repo_root: str, api_path: str
) -> JsonValue | None:
    """Read every page of a GitHub REST array payload.

    Args:
        repo_root [str]: Repository root used for token lookup.
        api_path [str]: API path beginning with `/repos/...` and returning an array.

    Returns:
        JsonValue | None: Combined array payload, or None if any required page fails.
    """
    combined_array: JsonArray = []
    page_number: int = 1
    while True:
        page_path: str = _build_paginated_array_path(api_path, page_number)
        page_payload: JsonValue | None = _read_github_api_json(repo_root, page_path)
        page_array: JsonArray | None = _as_json_array(page_payload)
        if page_array is None:
            missing_page: JsonValue | None = None
            return missing_page

        combined_array.extend(page_array)
        if len(page_array) < GITHUB_API_PAGE_SIZE:
            paginated_payload: JsonValue | None = combined_array
            return paginated_payload

        page_number += 1


def _read_github_paginated_object_array_json(
    repo_root: str,
    api_path: str,
    array_key: str,
) -> JsonValue | None:
    """Read every page of a GitHub REST object-wrapped array payload.

    Args:
        repo_root [str]: Repository root used for token lookup.
        api_path [str]: API path beginning with `/repos/...` and returning an object.
        array_key [str]: Object key that contains the paginated array.

    Returns:
        JsonValue | None: Object with the combined array payload, or None on page failure.
    """
    combined_array: JsonArray = []
    page_number: int = 1
    while True:
        page_path: str = _build_paginated_array_path(api_path, page_number)
        page_payload: JsonValue | None = _read_github_api_json(repo_root, page_path)
        page_object: JsonObject | None = _as_json_object(page_payload)
        if page_object is None:
            missing_page: JsonValue | None = None
            return missing_page

        page_array: JsonArray | None = _as_json_array(page_object.get(array_key))
        if page_array is None:
            malformed_page: JsonValue | None = None
            return malformed_page

        combined_array.extend(page_array)
        if len(page_array) < GITHUB_API_PAGE_SIZE:
            paginated_payload: JsonObject = {array_key: combined_array}
            combined_payload: JsonValue | None = paginated_payload
            return combined_payload

        page_number += 1


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


def _comment_author_login(comment_object: JsonObject) -> str | None:
    """Extract an issue comment author login.

    Args:
        comment_object [JsonObject]: Issue comment payload.

    Returns:
        str | None: Author login when available, otherwise None.
    """
    user_value: JsonValue | None = comment_object.get("user")
    user_object: JsonObject | None = _as_json_object(user_value)
    if user_object is None:
        missing_login: str | None = None
        return missing_login

    login_text: str | None = _as_non_empty_text(user_object.get("login"))
    return login_text


def _is_codex_no_major_issues_comment(comment_object: JsonObject) -> bool:
    """Check whether an issue comment is an authenticated Codex clean-review marker.

    Args:
        comment_object [JsonObject]: Issue comment payload.

    Returns:
        bool: True when the Codex bot authored a no-major-issues marker.
    """
    author_login: str | None = _comment_author_login(comment_object)
    if author_login != CODEX_REVIEW_BOT_LOGIN:
        is_codex_marker: bool = False
        return is_codex_marker

    body_text: str | None = _as_non_empty_text(comment_object.get("body"))
    if body_text is None:
        is_codex_marker = False
        return is_codex_marker

    if CODEX_NO_MAJOR_ISSUES_MARKER in body_text.lower():
        is_codex_marker = True
        return is_codex_marker

    is_codex_marker = False
    return is_codex_marker


def _reviewer_key(review_object: JsonObject, review_index: int) -> str:
    """Build a stable reviewer key for a GitHub review payload.

    Args:
        review_object [JsonObject]: Review object payload.
        review_index [int]: Chronological review index used when no user login exists.

    Returns:
        str: Reviewer identity key for latest-decision tracking.
    """
    user_value: JsonValue | None = review_object.get("user")
    user_object: JsonObject | None = _as_json_object(user_value)
    if user_object is None:
        fallback_key: str = f"anonymous-review-{review_index}"
        return fallback_key

    login_text: str | None = _as_non_empty_text(user_object.get("login"))
    if login_text is None:
        missing_login_key: str = f"anonymous-review-{review_index}"
        return missing_login_key

    reviewer_key: str = login_text
    return reviewer_key


def _classify_review_state(
    reviews_payload: JsonValue | None, comments_payload: JsonValue | None
) -> str:
    """Classify review state from GitHub reviews and Codex issue comments.

    Args:
        reviews_payload [JsonValue | None]: Pull request reviews API payload.
        comments_payload [JsonValue | None]: Issue comments API payload.

    Returns:
        str: Normalized review state summary.
    """
    reviews_array: JsonArray | None = _as_json_array(reviews_payload)
    if reviews_array is None:
        unknown_state: str = "unknown"
        return unknown_state

    latest_decisions_by_reviewer: dict[str, str] = {}
    for review_index, review_value in enumerate(reviews_array):
        review_object: JsonObject | None = _as_json_object(review_value)
        if review_object is None:
            continue
        state_text: str | None = _as_non_empty_text(review_object.get("state"))
        if state_text is None:
            continue
        normalized_state: str = state_text.lower()
        reviewer_key: str = _reviewer_key(review_object, review_index)
        if normalized_state == "dismissed":
            latest_decisions_by_reviewer.pop(reviewer_key, None)
            continue
        if normalized_state not in {"approved", "changes_requested"}:
            continue
        latest_decisions_by_reviewer[reviewer_key] = normalized_state

    for review_state in latest_decisions_by_reviewer.values():
        if review_state == "changes_requested":
            changes_requested_state: str = "changes_requested"
            return changes_requested_state

    comments_array: JsonArray | None = _as_json_array(comments_payload)
    if comments_array is not None:
        for comment_value in comments_array:
            comment_object: JsonObject | None = _as_json_object(comment_value)
            if comment_object is None:
                continue
            if _is_codex_no_major_issues_comment(comment_object):
                codex_state: str = "codex_no_major_issues"
                return codex_state

    for review_state in latest_decisions_by_reviewer.values():
        if review_state == "approved":
            approved_state: str = "approved"
            return approved_state

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


def _classify_check_state(
    status_payload: JsonValue | None, check_runs_payload: JsonValue | None
) -> str:
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
    if status_state is None or check_runs_state == "unknown":
        unknown_state: str = "unknown"
        return unknown_state
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
    remote_url: str | None = _run_git_command(
        repo_root, ("remote", "get-url", "origin")
    )
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
    mergeable_state: str | None = _as_non_empty_text(
        pull_request.get("mergeable_state")
    )
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

    reviews_payload: JsonValue | None = _read_github_paginated_array_json(
        repo_root,
        f"/repos/{owner}/{repo}/pulls/{pull_request_number}/reviews",
    )
    comments_payload: JsonValue | None = _read_github_paginated_array_json(
        repo_root,
        f"/repos/{owner}/{repo}/issues/{pull_request_number}/comments",
    )
    status_payload: JsonValue | None = _read_github_api_json(
        repo_root,
        f"/repos/{owner}/{repo}/commits/{head_sha}/status",
    )
    check_runs_payload: JsonValue | None = _read_github_paginated_object_array_json(
        repo_root,
        f"/repos/{owner}/{repo}/commits/{head_sha}/check-runs",
        "check_runs",
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


async def read_github_pull_request_status(
    repo_root: str,
) -> CockpitPullRequestObservation:
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
