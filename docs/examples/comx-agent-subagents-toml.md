# Project-scoped Codex subagent registration

`comx-agent agent codex-subagents` validates and materializes Codex-native custom
agent configuration from a strict JSON document. This is an ADE application
surface, not a Run lifecycle operation or a subagent scheduler.

The complete stock-informer dogfood example is
[`examples/codex-subagents/stock-informer.json`](../../examples/codex-subagents/stock-informer.json).
Its contract is:

```json
{
  "schema_version": "codex-subagent-registration.v1",
  "max_concurrent_threads_per_session": 5,
  "agents": [
    {
      "name": "luna_feature_auditor_max",
      "description": "Audit feature scope, repository fit, and implementation evidence.",
      "developer_instructions": "Review the requested feature against repository rules.",
      "model": "gpt-5.6-luna",
      "model_reasoning_effort": "max",
      "sandbox_mode": "read-only"
    }
  ]
}
```

Each agent requires all six agent fields. Names must start with a lowercase
letter and contain only lowercase letters, digits, `_`, or `-`. The model id is
restricted to a filesystem-neutral model token. Supported reasoning efforts are
`low`, `medium`, `high`, `xhigh`, and `max`; supported sandboxes are
`read-only` and `workspace-write`. The optional concurrency value must be from
1 through 64 and must be a JSON integer rather than a coerced string, float, or
boolean.

Use the commands in read-before-write order:

```bash
comx-agent agent codex-subagents validate WORKSPACE SPEC.json
comx-agent agent codex-subagents register WORKSPACE SPEC.json
comx-agent agent codex-subagents list WORKSPACE
```

`validate` does not create `.codex` or change any file. `register` creates or
updates only these project-local paths:

```text
WORKSPACE/.codex/config.toml
WORKSPACE/.codex/agents/<agent-name>.toml
```

Requested `[agents.<name>]` sections are replaced deterministically while
unrelated TOML sections and unrequested registrations remain in place. Agent
files not referenced by config are retained and reported as warnings; the
command does not delete them.

The updater reads existing config semantics before making targeted text edits.
Quoted agent tables such as `[agents."reviewer"]`, top-level
`agents.max_threads`, and quoted concurrency keys under `[agents]` are accepted
and normalized without rewriting unrelated sections. A shape that cannot be
updated without touching unrelated values is rejected instead of being guessed.

The registry rejects traversal names, absolute or non-deterministic agent file
references, unsafe sandbox values, malformed existing TOML, and symlinked
`.codex`, `agents`, config, or requested agent-file targets. User home,
user-global `~/.codex`, descendants of that directory, and symlink aliases are
not valid Workspaces. The command never launches Codex, OMX, or child agents.

Codex remains the source of truth for native selection, spawning, and session
semantics. A clean `list` result proves only that the project files are
internally consistent. Codex loads project `.codex/config.toml` only for trusted
projects, and comx-agent still reports native Codex subagent topology as unknown
without structured provider evidence. The project config shape follows the
[Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml).
