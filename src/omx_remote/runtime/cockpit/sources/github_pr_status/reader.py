"""Read-only GitHub PR evidence source for cockpit operating decisions."""

from __future__ import annotations

import urllib.parse

from omx_remote.adapter_types.json_types import JsonArray, JsonObject, JsonValue
from omx_remote.execution.async_boundary import run_blocking_call
from omx_remote.runtime.cockpit.sources.github_pr_status.api_client import (
    _as_json_array,
    _as_json_object,
    _as_non_empty_text,
    _as_positive_int,
    _read_github_api_json,
    _read_github_paginated_array_json,
    _read_github_paginated_object_array_json,
)
from omx_remote.runtime.cockpit.sources.github_pr_status.classification import (
    _classify_check_state,
    _classify_review_state,
)
from omx_remote.runtime.cockpit.sources.github_pr_status.git_repo import (
    _parse_github_owner_repo,
    _run_git_command,
)
from omx_remote.schemas.cockpit.snapshot_schemas import CockpitPullRequestObservation


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


def _select_pull_request_target_repo(
    repo_root: str,
    origin_owner_repo: tuple[str, str],
) -> tuple[str, str]:
    """Select the repository that owns the PR list to query.

    Args:
        repo_root [str]: Repository root used to read optional remotes.
        origin_owner_repo [tuple[str, str]]: Parsed owner/repo from origin.

    Returns:
        tuple[str, str]: Owner/repo that should receive the pull-request query.
    """
    origin_owner, origin_repo = origin_owner_repo
    upstream_url: str | None = _run_git_command(
        repo_root,
        ("remote", "get-url", "upstream"),
    )
    if upstream_url is None:
        target_repo: tuple[str, str] = (origin_owner, origin_repo)
        return target_repo

    upstream_owner_repo: tuple[str, str] | None = _parse_github_owner_repo(upstream_url)
    if upstream_owner_repo is None:
        target_repo = (origin_owner, origin_repo)
        return target_repo

    upstream_owner, upstream_repo = upstream_owner_repo
    if upstream_repo != origin_repo:
        target_repo = (origin_owner, origin_repo)
        return target_repo

    target_repo = (upstream_owner, upstream_repo)
    return target_repo


def _build_pull_request_query_path(
    target_owner: str,
    repo: str,
    head_owner: str,
    branch: str,
) -> str:
    """Build the open pull request query path for one branch.

    Args:
        target_owner [str]: GitHub repository owner whose PR list should be queried.
        repo [str]: GitHub repository name.
        head_owner [str]: GitHub owner for the branch head.
        branch [str]: Current branch name.

    Returns:
        str: GitHub REST API path and query string.
    """
    encoded_head: str = urllib.parse.quote(f"{head_owner}:{branch}", safe=":/")
    path: str = f"/repos/{target_owner}/{repo}/pulls?head={encoded_head}&state=open"
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

    origin_owner, _origin_repo = owner_repo
    target_owner, target_repo = _select_pull_request_target_repo(repo_root, owner_repo)
    pulls_path: str = _build_pull_request_query_path(
        target_owner,
        target_repo,
        origin_owner,
        branch,
    )
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
        f"/repos/{target_owner}/{target_repo}/pulls/{pull_request_number}/reviews",
    )
    comments_payload: JsonValue | None = _read_github_paginated_array_json(
        repo_root,
        f"/repos/{target_owner}/{target_repo}/issues/{pull_request_number}/comments",
    )
    status_payload: JsonValue | None = _read_github_api_json(
        repo_root,
        f"/repos/{target_owner}/{target_repo}/commits/{head_sha}/status",
    )
    check_runs_payload: JsonValue | None = _read_github_paginated_object_array_json(
        repo_root,
        f"/repos/{target_owner}/{target_repo}/commits/{head_sha}/check-runs",
        "check_runs",
    )
    review_state: str = _classify_review_state(
        reviews_payload,
        comments_payload,
        head_sha,
    )
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
    observation: CockpitPullRequestObservation = await run_blocking_call(
        _read_pull_request_status_sync,
        repo_root,
    )
    return observation
