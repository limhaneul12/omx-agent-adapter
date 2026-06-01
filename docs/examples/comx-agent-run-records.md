# Agent Remote Run Records

Use `comx-agent run --record-run` to persist a typed dry-run plan and handoff artifact under `.comx-agent/runs/`. Records make composed-command intent replayable without trusting terminal scrollback.

Human flow:

```bash
comx-agent run builtin:review-gate --cwd . --dry-run --json --record-run
comx-agent runs list --cwd .
comx-agent runs show <run-id> --cwd . --json
comx-agent runs handoff <run-id> --cwd .
comx-agent runs replay-plan <run-id> --cwd . --dry-run --json
```

Agent JSON contract example from `comx-agent run builtin:review-gate --cwd . --dry-run --json --record-run`:

```json
{
  "plan": {
    "command_id": "review-gate",
    "qualified_id": "builtin:review-gate",
    "source": "builtin",
    "namespace": "workflow",
    "category": "lifecycle",
    "description": "Run specialist review lanes and produce an approve/block review verdict.",
    "risk": "long_running",
    "dry_run": true,
    "steps": [
      {
        "index": 1,
        "command": "local",
        "agent": null,
        "native_argv": ["git", "diff", "--check"],
        "codex_search": false,
        "codex_sandbox": null,
        "prompt_file": null,
        "prompt_exists": null,
        "prompt_sha256": null,
        "inline_prompt": null,
        "mcp_server": null,
        "mcp_tool": null,
        "mcp_arguments": {},
        "expected_artifacts": [],
        "role_lanes": [],
        "risk": "long_running",
        "blocked_reasons": []
      }
    ],
    "blocked_reasons": []
  },
  "run_record": {
    "run_id": "20260524T200646Z-review-gate",
    "command_id": "review-gate",
    "qualified_id": "builtin:review-gate",
    "source": "builtin",
    "cwd": "/repo",
    "started_at": "2026-05-24T20:06:46.398842+00:00",
    "finished_at": "2026-05-24T20:06:46.398842+00:00",
    "status": "planned",
    "dry_run": true,
    "native_commands": [
      {"index": 1, "argv": ["git", "diff", "--check"]}
    ],
    "artifacts": [
      {"kind": "run", "path": "/repo/.comx-agent/runs/20260524T200646Z-review-gate/run.json"},
      {"kind": "plan", "path": "/repo/.comx-agent/runs/20260524T200646Z-review-gate/plan.json"},
      {"kind": "handoff", "path": "/repo/.comx-agent/runs/20260524T200646Z-review-gate/handoff.md"}
    ],
    "verification": {"status": "not_run", "evidence": "dry-run record"},
    "plan_path": "/repo/.comx-agent/runs/20260524T200646Z-review-gate/plan.json",
    "stdout_log_path": "/repo/.comx-agent/runs/20260524T200646Z-review-gate/stdout.log",
    "stderr_log_path": "/repo/.comx-agent/runs/20260524T200646Z-review-gate/stderr.log",
    "handoff_path": "/repo/.comx-agent/runs/20260524T200646Z-review-gate/handoff.md"
  }
}
```

Run records are local runtime artifacts. Keep `.comx-agent/runs/` out of commits unless a maintainer explicitly asks for a sanitized fixture.
