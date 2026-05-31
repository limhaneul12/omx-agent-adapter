# Agent Remote Subagents TOML

Use `agent-remote agents` to validate repo-local TOML subagent configuration and materialize supported entries into Codex native agent files.

Minimal `.agent-remote.toml` shape:

```toml
[agents.reviewer]
enabled = true
provider = "codex"
role = "code-reviewer"
model = "gpt-5.5"
effort = "high"
persona = "Review the current diff against repository rules."
routing_hints = ["review", "current-diff"]
```

Agent ids become generated filenames during Codex materialization. Keep them filesystem-safe: start with a letter or digit and use only letters, digits, `-`, or `_`.

Human flow:

```bash
agent-remote agents validate --cwd .
agent-remote agents list --cwd .
agent-remote agents plan-apply-codex --cwd . --json
agent-remote agents apply-codex --cwd . --dry-run --json
agent-remote agents codex-status --cwd . --json
```

Materialization targets:

- `--target project` writes `.codex/agents/<agent>.toml`. This is the Codex-documented project-scoped location and remains the default.
- `--target global --namespace <project-slug>` writes `~/.codex/agents/<project-slug>-<agent>.toml`. Use this for non-interactive `codex exec` dogfood when project-local custom agents are not visible to the spawn surface.

Global target preview:

```bash
agent-remote agents plan-apply-codex --cwd . --target global --namespace my-project --json
agent-remote agents apply-codex --cwd . --target global --namespace my-project --dry-run --json
agent-remote agents codex-status --cwd . --target global --namespace my-project --json
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
  "target": "project",
  "files": [],
  "warning_count": 1,
  "warnings": [
    "No agent config found at .agent-remote.toml."
  ]
}
```

Materialization rule: use `plan-apply-codex` or `apply-codex --dry-run` before writing Codex agent TOML. Keep repo source in `.agent-remote.toml`, use project target for documented local files, and use global namespaced target only when the execution surface has proven it needs globally discoverable agent names.
