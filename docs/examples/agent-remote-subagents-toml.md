# Agent Remote Subagents TOML

Use `agent-remote agents` to validate repo-local TOML subagent configuration and materialize supported entries into project-local Codex native agent files.

Minimal `.agent-remote.toml` shape:

```toml
[[agents]]
id = "reviewer"
role = "code-reviewer"
provider = "codex"
model = "gpt-5.5"
reasoning_effort = "high"
enabled = true
description = "Review the current diff against repository rules."
instructions = "Focus on correctness, tests, type safety, and repository conventions."
```

Human flow:

```bash
agent-remote agents validate --cwd .
agent-remote agents list --cwd .
agent-remote agents plan-apply-codex --cwd . --json
agent-remote agents apply-codex --cwd . --dry-run --json
agent-remote agents codex-status --cwd . --json
```

Agent JSON contract example from `agent-remote agents validate --cwd . --json` when no config exists yet:

```json
{
  "valid": true,
  "config_path": ".agent-remote.toml",
  "agent_count": 0,
  "warnings": [
    "No agent config found at .agent-remote.toml."
  ],
  "error": null
}
```

Codex materialization status example from `agent-remote agents codex-status --cwd . --json`:

```json
{
  "up_to_date": true,
  "supported": true,
  "files": [],
  "warning_count": 1,
  "warnings": [
    "No agent config found at .agent-remote.toml."
  ]
}
```

Materialization rule: use `plan-apply-codex` or `apply-codex --dry-run` before writing `.codex/agents/*.toml`. The adapter should preserve Codex-native semantics instead of inventing a separate agent framework.
