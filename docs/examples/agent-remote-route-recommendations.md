# Agent Remote Route Recommendations

Use `agent-remote route recommend` when a human or agent needs an evidence-backed lane recommendation for a task. The route policy reads current capabilities, configured agents, recipes, and active runtime modes before recommending or blocking alternatives.

Human flow:

```bash
agent-remote cockpit snapshot --cwd .
agent-remote route recommend --task "review current diff" --cwd .
agent-remote route explain project-command
agent-remote preflight route codex-exec --cwd .
```

Agent JSON contract example from `agent-remote route recommend --task "review current diff" --cwd . --json`:

```json
{
  "task": "review current diff",
  "classification": {
    "task": "review current diff",
    "size": "small",
    "task_type": "review",
    "needs_parallelism": false,
    "needs_durable_state": false,
    "signals": [
      "current_diff"
    ]
  },
  "recommendations": [
    {
      "route": "project_command",
      "status": "recommended",
      "confidence": "high",
      "reason": "The task is a review and the built-in diff review recipe is available.",
      "command_id": "builtin:review-diff",
      "blocked_by": []
    }
  ],
  "blocked_alternatives": [
    {
      "route": "omx_team",
      "status": "blocked",
      "confidence": "low",
      "reason": "OMX Team is not currently safe for fanout.",
      "command_id": null,
      "blocked_by": [
        "active runtime modes: ultragoal"
      ]
    }
  ],
  "warnings": []
}
```

Preflight JSON example from `agent-remote preflight run review-diff --cwd . --json`:

```json
{
  "status": "passed",
  "checks": [
    {
      "category": "git_state",
      "severity": "info",
      "summary": "git state is clean",
      "detail": "git status --short returned no changes.",
      "blocks_execution": false,
      "evidence": null
    },
    {
      "category": "tool_availability",
      "severity": "info",
      "summary": "codex is available",
      "detail": "codex resolves to /opt/homebrew/bin/codex.",
      "blocks_execution": false,
      "evidence": "/opt/homebrew/bin/codex"
    }
  ],
  "blockers": [],
  "warnings": [],
  "command_id": "review-diff",
  "qualified_id": "builtin:review-diff",
  "route": null
}
```

Recommendation rule: a recommended route is not a permission slip to mutate. Run the matching `preflight` command and inspect `blocked_alternatives` before launching Team, Ralph, UltraGoal, or any external command.
