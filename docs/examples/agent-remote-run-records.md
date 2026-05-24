# Agent Remote Run Records

Use `agent-remote run --record-run` to persist a typed dry-run plan and handoff artifact under `.agent-remote/runs/`. Records make composed-command intent replayable without trusting terminal scrollback.

Human flow:

```bash
agent-remote run review-diff --cwd . --dry-run --json --record-run
agent-remote runs list --cwd .
agent-remote runs show <run-id> --cwd . --json
agent-remote runs handoff <run-id> --cwd .
agent-remote runs replay-plan <run-id> --cwd . --dry-run --json
```

Agent JSON contract example from `agent-remote run review-diff --cwd . --dry-run --json --record-run`:

```json
{
  "plan": {
    "command_id": "review-diff",
    "qualified_id": "builtin:review-diff",
    "source": "builtin",
    "description": "Review the current git diff against repository rules.",
    "risk": "read_only",
    "dry_run": true,
    "steps": [
      {
        "index": 1,
        "command": "codex_exec",
        "agent": null,
        "native_argv": [
          "codex",
          "exec",
          "--json",
          "--output-last-message",
          ".agent-remote/runs/review-diff/final-message.md",
          "Review the current git diff against the repository rules. Return findings, risks, and an approval recommendation."
        ],
        "prompt_file": null,
        "prompt_exists": null,
        "prompt_sha256": null,
        "inline_prompt": "Review the current git diff against the repository rules. Return findings, risks, and an approval recommendation.",
        "expected_artifacts": [
          ".agent-remote/runs/review-diff/final-message.md"
        ],
        "risk": "read_only",
        "blocked_reasons": []
      }
    ],
    "blocked_reasons": []
  },
  "run_record": {
    "run_id": "20260524T200646Z-review-diff",
    "command_id": "review-diff",
    "qualified_id": "builtin:review-diff",
    "source": "builtin",
    "cwd": "/repo",
    "started_at": "2026-05-24T20:06:46.398842+00:00",
    "finished_at": "2026-05-24T20:06:46.398842+00:00",
    "status": "planned",
    "dry_run": true,
    "native_commands": [
      {
        "index": 1,
        "argv": [
          "codex",
          "exec",
          "--json",
          "--output-last-message",
          "/repo/.agent-remote/runs/review-diff/final-message.md",
          "Review the current git diff against the repository rules. Return findings, risks, and an approval recommendation."
        ]
      }
    ],
    "artifacts": [
      {
        "kind": "run",
        "path": "/repo/.agent-remote/runs/20260524T200646Z-review-diff/run.json"
      },
      {
        "kind": "plan",
        "path": "/repo/.agent-remote/runs/20260524T200646Z-review-diff/plan.json"
      },
      {
        "kind": "handoff",
        "path": "/repo/.agent-remote/runs/20260524T200646Z-review-diff/handoff.md"
      }
    ],
    "verification": {
      "status": "not_run",
      "evidence": "dry-run record"
    },
    "plan_path": "/repo/.agent-remote/runs/20260524T200646Z-review-diff/plan.json",
    "stdout_log_path": "/repo/.agent-remote/runs/20260524T200646Z-review-diff/stdout.log",
    "stderr_log_path": "/repo/.agent-remote/runs/20260524T200646Z-review-diff/stderr.log",
    "handoff_path": "/repo/.agent-remote/runs/20260524T200646Z-review-diff/handoff.md"
  }
}
```

Run records are local runtime artifacts. Keep `.agent-remote/runs/` out of commits unless a maintainer explicitly asks for a sanitized fixture.
