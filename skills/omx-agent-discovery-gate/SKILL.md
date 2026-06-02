---
name: omx-agent-discovery-gate
description: Use when the user mentions discovery-gate, wants to clarify an idea before research or company-run, needs no-build/reroute/readiness screening, or wants OMX deep-interview integrated as a gate rather than a separate public adapter command.
---

# omx-agent discovery-gate

Use `builtin:discovery-gate` as Gate 0: decide whether an idea is worth deeper research, PRD writing, or `company-run` before expensive council/Team work begins.

## When to use

- The task is still an idea, product direction, or vague goal.
- You need ambiguity scoring and no-build/reroute checks.
- You need to decide between `needs-interview`, `ready-for-research`, `ready-for-prd`, `ready-for-company-run`, `reroute`, or `no-build`.
- You want OMX `deep-interview` as a handoff point without adding it as a public adapter command.

## Do not use

- For already-scoped implementation tasks with accepted PRD/test spec.
- To bypass research or PRD gates.
- To launch Team directly.

## Standard usage

```bash
agent-remote commands show builtin:discovery-gate --cwd . --json
agent-remote run builtin:discovery-gate --cwd . --dry-run --task "<idea or goal>" --json
agent-remote run builtin:discovery-gate --cwd . --execute --autonomy agent --task "<idea or goal>" --json
```

Development fallback:

```bash
PYTHONPATH=src:src/omx_remote uv run python omx_agent_adapter_cli.py run builtin:discovery-gate --cwd . --execute --autonomy agent --task "<idea or goal>" --json
```

CLI preview:

```text
comx-agent run builtin:discovery-gate --task "<idea or goal>" --cwd . --dry-run
```

## Expected artifacts

The command prompt requires a `DiscoveryGateResult`-compatible decision packet and related artifacts, including:

- discovery summary
- ambiguity map
- no-build / ROI gate
- reroute recommendation when smaller commands are better
- deep-interview handoff when ambiguity is material

## Output interpretation

- `ready-for-company-run`: proceed to `company-run` if the task is build-oriented and worth Team/subagents.
- `ready-for-research`: run `research-brief` before PRD.
- `ready-for-prd`: run `idea-to-prd`.
- `needs-interview`: use OMX deep-interview and resume with the clarified answer.
- `no-build` or `reroute`: do not spend company-run tokens.
