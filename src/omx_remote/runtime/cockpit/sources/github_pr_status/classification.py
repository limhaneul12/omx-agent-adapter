"""Review and check classifiers for GitHub PR cockpit evidence."""

from __future__ import annotations

from omx_remote.adapter_types.json_types import JsonArray, JsonObject, JsonValue
from omx_remote.runtime.cockpit.sources.github_pr_status.api_client import (
    _as_json_array,
    _as_json_object,
    _as_non_empty_text,
)

CODEX_NO_MAJOR_ISSUES_MARKER = "didn't find any major issues"
CODEX_REVIEW_BOT_LOGIN = "chatgpt-codex-connector[bot]"


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


def _body_mentions_head_sha(body_text: str, head_sha: str) -> bool:
    """Check whether text names the current head commit.

    Args:
        body_text [str]: Text to inspect.
        head_sha [str]: Current PR head SHA.

    Returns:
        bool: True when body text contains the full or short head SHA.
    """
    normalized_body: str = body_text.lower()
    normalized_head_sha: str = head_sha.lower()
    short_head_sha: str = normalized_head_sha[:10]
    if normalized_head_sha in normalized_body or short_head_sha in normalized_body:
        mentions_head_sha: bool = True
        return mentions_head_sha

    mentions_head_sha = False
    return mentions_head_sha


def _is_codex_no_major_issues_comment(
    comment_object: JsonObject,
    head_sha: str,
) -> bool:
    """Check whether an issue comment is a current Codex clean-review marker.

    Args:
        comment_object [JsonObject]: Issue comment payload.
        head_sha [str]: Current PR head SHA.

    Returns:
        bool: True when the Codex bot authored a no-major-issues marker for head.
    """
    author_login: str | None = _comment_author_login(comment_object)
    if author_login != CODEX_REVIEW_BOT_LOGIN:
        is_codex_marker: bool = False
        return is_codex_marker

    body_text: str | None = _as_non_empty_text(comment_object.get("body"))
    if body_text is None:
        is_codex_marker = False
        return is_codex_marker

    if CODEX_NO_MAJOR_ISSUES_MARKER not in body_text.lower():
        is_codex_marker = False
        return is_codex_marker

    if not _body_mentions_head_sha(body_text, head_sha):
        is_codex_marker = False
        return is_codex_marker

    is_codex_marker = True
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
    reviews_payload: JsonValue | None,
    comments_payload: JsonValue | None,
    head_sha: str,
) -> str:
    """Classify review state from GitHub reviews and Codex issue comments.

    Args:
        reviews_payload [JsonValue | None]: Pull request reviews API payload.
        comments_payload [JsonValue | None]: Issue comments API payload.
        head_sha [str]: Current PR head SHA.

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
            if _is_codex_no_major_issues_comment(comment_object, head_sha):
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
            continue
        unknown_state: str = "unknown"
        return unknown_state

    if saw_success_like_run:
        success_state: str = "success"
        return success_state

    unknown_state = "unknown"
    return unknown_state


def _classify_combined_status(status_payload: JsonValue | None) -> str:
    """Classify GitHub combined status evidence.

    Args:
        status_payload [JsonValue | None]: Combined status API payload.

    Returns:
        str: Normalized combined status evidence state.
    """
    status_object: JsonObject | None = _as_json_object(status_payload)
    if status_object is None:
        unknown_state: str = "unknown"
        return unknown_state

    statuses_array: JsonArray | None = _as_json_array(status_object.get("statuses"))
    if statuses_array is not None and len(statuses_array) == 0:
        no_statuses_state: str = "no_statuses"
        return no_statuses_state

    status_text: str | None = _as_non_empty_text(status_object.get("state"))
    if status_text is None:
        unknown_state = "unknown"
        return unknown_state

    status_state: str = status_text
    return status_state


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
    status_state: str = _classify_combined_status(status_payload)

    check_runs_state: str = _classify_check_runs(check_runs_payload)
    if status_state in {"failure", "error"} or check_runs_state == "failure":
        failed_state: str = "failure"
        return failed_state
    if status_state == "no_statuses" and check_runs_state == "no_check_runs":
        no_checks_state: str = "no_checks"
        return no_checks_state
    if status_state == "pending" or check_runs_state == "pending":
        pending_state: str = "pending"
        return pending_state
    if status_state == "unknown" or check_runs_state == "unknown":
        unknown_state: str = "unknown"
        return unknown_state
    if status_state == "success" or check_runs_state == "success":
        success_state: str = "success"
        return success_state
    if status_state not in {"no_statuses", "unknown"}:
        observed_status_state: str = status_state
        return observed_status_state

    unknown_state: str = "unknown"
    return unknown_state
