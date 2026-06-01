---
name: omx-agent-idea-to-prd
description: Use when the user mentions idea-to-prd, wants to turn an idea and research into PRD, test spec, execution brief, risks, assumptions, rejected alternatives, and implementation-readiness recommendation before any implementation.
---

# omx-agent idea-to-prd

Use `builtin:idea-to-prd` after discovery/research has enough evidence and before implementation starts.

## When to use

- You have an accepted idea and need planning artifacts.
- Research is complete enough to define scope and non-goals.
- Company-run reaches the planning phase.
- You need PRD, test spec, execution brief, risks, assumptions, rejected alternatives, and readiness verdict.

## Do not use

- Before resolving material ambiguity.
- As an implementation command.
- To launch Team or mutate product code.

## Standard usage

```bash
agent-remote commands show builtin:idea-to-prd --cwd . --json
agent-remote run builtin:idea-to-prd --cwd . --dry-run --task "<accepted idea plus evidence>" --json
agent-remote run builtin:idea-to-prd --cwd . --execute --autonomy agent --task "<accepted idea plus evidence>" --json
```

Development fallback:

```bash
PYTHONPATH=src:src/omx_remote uv run python omx_agent_adapter_cli.py run builtin:idea-to-prd --cwd . --execute --autonomy agent --task "<accepted idea plus evidence>" --json
```

TUI preview:

```text
/run builtin:idea-to-prd --task "<accepted idea plus evidence>"
```

## Expected artifacts

- PRD
- test spec
- execution brief
- risks and assumptions
- rejected alternatives
- implementation-readiness recommendation

## Output interpretation

If readiness is blocked, do not proceed to implementation. Resolve ambiguity or rerun research/discovery. If readiness is clear, move to `implementation-kickoff` or let `company-run` continue into its executive gate.
