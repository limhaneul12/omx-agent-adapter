# Agent Remote Route Recommendations

Use `comx-agent route recommend` when a human or agent needs an evidence-backed lane recommendation for a task. The route policy reads current capabilities, configured agents, recipes, and active runtime modes before recommending or blocking alternatives.

Human flow:

```bash
comx-agent cockpit snapshot --cwd .
comx-agent route recommend --task "review current diff" --cwd .
comx-agent route explain project-command
comx-agent preflight run builtin:review-gate --cwd . --json
```

Agent JSON contract example from `comx-agent route recommend --task "review current diff" --cwd . --json`:

```json
{
  "task": "review current diff",
  "classification": {
    "task": "review current diff",
    "size": "small",
    "task_type": "review",
    "needs_parallelism": false,
    "needs_durable_state": false,
    "needs_discovery": false,
    "signals": ["current_diff"]
  },
  "recommendations": [
    {
      "route": "project_command",
      "status": "recommended",
      "confidence": "high",
      "reason": "The task is a review and the built-in review gate recipe is available.",
      "command_id": "builtin:review-gate",
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
      "blocked_by": ["active runtime modes: ultragoal"]
    }
  ],
  "warnings": []
}
```

Discovery recommendation example for an ambiguous company-run request:

```json
{
  "task": "company-run this vague product idea with unclear non-goals",
  "classification": {
    "task": "company-run this vague product idea with unclear non-goals",
    "size": "medium",
    "task_type": "implementation",
    "needs_parallelism": false,
    "needs_durable_state": false,
    "needs_discovery": true,
    "signals": ["needs_discovery", "company_run_requested"]
  },
  "recommendations": [
    {
      "route": "project_command",
      "status": "recommended",
      "confidence": "high",
      "reason": "The task is broad, ambiguous, or company-run-sized; discovery-gate should settle non-goals, decision boundaries, ROI/no-build, and deep-interview handoff before expensive work.",
      "command_id": "builtin:discovery-gate",
      "blocked_by": []
    }
  ],
  "blocked_alternatives": [],
  "warnings": []
}
```

Preflight JSON example from `comx-agent preflight run builtin:review-gate --cwd . --json`:

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
  "command_id": "review-gate",
  "qualified_id": "builtin:review-gate",
  "route": null
}
```

Recommendation rule: a recommended route is not a permission slip to mutate. Run the matching `preflight` command and inspect `blocked_alternatives` before launching Team, Ralph, UltraGoal, or any external command.
