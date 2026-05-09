import asyncio

from omx_remote.runtime.cockpit import github_pr_status
from omx_remote.runtime.cockpit.github_pr_status import read_github_pull_request_status


def test_read_github_pull_request_status_reports_open_pr_review_and_checks(
    monkeypatch,
    tmp_path,
) -> None:
    def fake_run_git_command(repo_root: str, arguments: tuple[str, ...]) -> str | None:
        assert repo_root == str(tmp_path)
        outputs: dict[tuple[str, ...], str] = {
            ("remote", "get-url", "origin"): "https://github.com/limhaneul12/omx-agent-adapter.git",
            ("branch", "--show-current"): "feat/cockpit-pr-status-source",
        }
        return outputs[arguments]

    def fake_read_github_api_json(repo_root: str, api_path: str):
        assert repo_root == str(tmp_path)
        payloads = {
            "/repos/limhaneul12/omx-agent-adapter/pulls?head=limhaneul12:feat/cockpit-pr-status-source&state=open": [
                {
                    "number": 10,
                    "state": "open",
                    "html_url": "https://github.com/limhaneul12/omx-agent-adapter/pull/10",
                    "mergeable_state": "clean",
                    "head": {"sha": "abc123"},
                }
            ],
            "/repos/limhaneul12/omx-agent-adapter/pulls/10/reviews": [],
            "/repos/limhaneul12/omx-agent-adapter/issues/10/comments": [
                {"body": "Didn't find any major issues. Breezy!"}
            ],
            "/repos/limhaneul12/omx-agent-adapter/commits/abc123/status": {
                "state": "success"
            },
            "/repos/limhaneul12/omx-agent-adapter/commits/abc123/check-runs": {
                "check_runs": [
                    {"name": "tests", "status": "completed", "conclusion": "success"}
                ]
            },
        }
        return payloads[api_path]

    monkeypatch.setattr(github_pr_status, "_run_git_command", fake_run_git_command)
    monkeypatch.setattr(
        github_pr_status,
        "_read_github_api_json",
        fake_read_github_api_json,
    )

    observation = asyncio.run(read_github_pull_request_status(str(tmp_path)))

    assert observation.provider == "github"
    assert observation.branch == "feat/cockpit-pr-status-source"
    assert observation.status == "open"
    assert observation.pull_request_number == 10
    assert observation.mergeable_state == "clean"
    assert observation.review_state == "codex_no_major_issues"
    assert observation.check_state == "success"
    assert observation.url == "https://github.com/limhaneul12/omx-agent-adapter/pull/10"
    assert "PR #10" in observation.detail
    assert "codex_no_major_issues" in observation.detail
    assert "success" in observation.detail


def test_read_github_pull_request_status_reports_missing_open_pr(
    monkeypatch,
    tmp_path,
) -> None:
    def fake_run_git_command(repo_root: str, arguments: tuple[str, ...]) -> str | None:
        outputs: dict[tuple[str, ...], str] = {
            ("remote", "get-url", "origin"): "https://github.com/limhaneul12/omx-agent-adapter.git",
            ("branch", "--show-current"): "main",
        }
        return outputs[arguments]

    def fake_read_github_api_json(repo_root: str, api_path: str):
        assert api_path == "/repos/limhaneul12/omx-agent-adapter/pulls?head=limhaneul12:main&state=open"
        return []

    monkeypatch.setattr(github_pr_status, "_run_git_command", fake_run_git_command)
    monkeypatch.setattr(
        github_pr_status,
        "_read_github_api_json",
        fake_read_github_api_json,
    )

    observation = asyncio.run(read_github_pull_request_status(str(tmp_path)))

    assert observation.branch == "main"
    assert observation.status == "no_open_pull_request"
    assert observation.pull_request_number is None
    assert observation.review_state == "not_applicable"
    assert observation.check_state == "not_applicable"
    assert observation.url is None
    assert "No open GitHub pull request" in observation.detail


def test_read_github_pull_request_status_reports_api_unavailable(
    monkeypatch,
    tmp_path,
) -> None:
    def fake_run_git_command(repo_root: str, arguments: tuple[str, ...]) -> str | None:
        outputs: dict[tuple[str, ...], str] = {
            ("remote", "get-url", "origin"): "https://github.com/limhaneul12/omx-agent-adapter.git",
            ("branch", "--show-current"): "feat/cockpit-pr-status-source",
        }
        return outputs[arguments]

    def fake_read_github_api_json(repo_root: str, api_path: str):
        return None

    monkeypatch.setattr(github_pr_status, "_run_git_command", fake_run_git_command)
    monkeypatch.setattr(
        github_pr_status,
        "_read_github_api_json",
        fake_read_github_api_json,
    )

    observation = asyncio.run(read_github_pull_request_status(str(tmp_path)))

    assert observation.branch == "feat/cockpit-pr-status-source"
    assert observation.status == "unavailable"
    assert observation.pull_request_number is None
    assert observation.review_state == "unknown"
    assert observation.check_state == "unknown"
    assert observation.warnings == ("open pull request query failed",)
    assert "unavailable" in observation.detail


def test_read_github_pull_request_status_prioritizes_blocking_reviews(
    monkeypatch,
    tmp_path,
) -> None:
    def fake_run_git_command(repo_root: str, arguments: tuple[str, ...]) -> str | None:
        outputs: dict[tuple[str, ...], str] = {
            ("remote", "get-url", "origin"): "https://github.com/limhaneul12/omx-agent-adapter.git",
            ("branch", "--show-current"): "feat/cockpit-pr-status-source",
        }
        return outputs[arguments]

    def fake_read_github_api_json(repo_root: str, api_path: str):
        payloads = {
            "/repos/limhaneul12/omx-agent-adapter/pulls?head=limhaneul12:feat/cockpit-pr-status-source&state=open": [
                {
                    "number": 10,
                    "state": "open",
                    "html_url": "https://github.com/limhaneul12/omx-agent-adapter/pull/10",
                    "mergeable_state": "clean",
                    "head": {"sha": "abc123"},
                }
            ],
            "/repos/limhaneul12/omx-agent-adapter/pulls/10/reviews": [
                {"state": "CHANGES_REQUESTED"}
            ],
            "/repos/limhaneul12/omx-agent-adapter/issues/10/comments": [
                {"body": "Didn't find any major issues. Breezy!"}
            ],
            "/repos/limhaneul12/omx-agent-adapter/commits/abc123/status": {
                "state": "success"
            },
            "/repos/limhaneul12/omx-agent-adapter/commits/abc123/check-runs": {
                "check_runs": [
                    {"name": "tests", "status": "completed", "conclusion": "success"}
                ]
            },
        }
        return payloads[api_path]

    monkeypatch.setattr(github_pr_status, "_run_git_command", fake_run_git_command)
    monkeypatch.setattr(
        github_pr_status,
        "_read_github_api_json",
        fake_read_github_api_json,
    )

    observation = asyncio.run(read_github_pull_request_status(str(tmp_path)))

    assert observation.review_state == "changes_requested"
    assert "changes_requested" in observation.detail


def test_read_github_pull_request_status_uses_latest_reviewer_decision(
    monkeypatch,
    tmp_path,
) -> None:
    def fake_run_git_command(repo_root: str, arguments: tuple[str, ...]) -> str | None:
        outputs: dict[tuple[str, ...], str] = {
            ("remote", "get-url", "origin"): "https://github.com/limhaneul12/omx-agent-adapter.git",
            ("branch", "--show-current"): "feat/cockpit-pr-status-source",
        }
        return outputs[arguments]

    def fake_read_github_api_json(repo_root: str, api_path: str):
        payloads = {
            "/repos/limhaneul12/omx-agent-adapter/pulls?head=limhaneul12:feat/cockpit-pr-status-source&state=open": [
                {
                    "number": 10,
                    "state": "open",
                    "html_url": "https://github.com/limhaneul12/omx-agent-adapter/pull/10",
                    "mergeable_state": "clean",
                    "head": {"sha": "abc123"},
                }
            ],
            "/repos/limhaneul12/omx-agent-adapter/pulls/10/reviews": [
                {"state": "CHANGES_REQUESTED", "user": {"login": "reviewer-a"}},
                {"state": "APPROVED", "user": {"login": "reviewer-a"}},
            ],
            "/repos/limhaneul12/omx-agent-adapter/issues/10/comments": [],
            "/repos/limhaneul12/omx-agent-adapter/commits/abc123/status": {
                "state": "success"
            },
            "/repos/limhaneul12/omx-agent-adapter/commits/abc123/check-runs": {
                "check_runs": [
                    {"name": "tests", "status": "completed", "conclusion": "success"}
                ]
            },
        }
        return payloads[api_path]

    monkeypatch.setattr(github_pr_status, "_run_git_command", fake_run_git_command)
    monkeypatch.setattr(
        github_pr_status,
        "_read_github_api_json",
        fake_read_github_api_json,
    )

    observation = asyncio.run(read_github_pull_request_status(str(tmp_path)))

    assert observation.review_state == "approved"
    assert "approved" in observation.detail
