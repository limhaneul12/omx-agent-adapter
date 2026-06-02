---
name: omx-agent-research-brief
description: Use when the user mentions research-brief or needs a source-backed research artifact with confidence labels, uncertainty, citations, feasibility evidence, or market/technical/risk findings before PRD or company-run.
---

# omx-agent research-brief

Use `builtin:research-brief` when current evidence matters before deciding what to build or how to build it.

## When to use

- The user asks for external/current research.
- Discovery-gate says `ready-for-research`.
- A PRD needs market, technical, risk, or competitor evidence.
- Company-run needs stronger evidence before proceed/no-build voting.

## Do not use

- For purely repo-local questions that `route-next` can classify.
- To fabricate citations from memory.
- As a PRD writer; hand off to `idea-to-prd` after research is sufficient.

## Standard usage

```bash
agent-remote commands show builtin:research-brief --cwd . --json
agent-remote run builtin:research-brief --cwd . --dry-run --task "<research objective>" --json
agent-remote run builtin:research-brief --cwd . --execute --autonomy agent --task "<research objective>" --json
```

Development fallback:

```bash
PYTHONPATH=src:src/omx_remote uv run python omx_agent_adapter_cli.py run builtin:research-brief --cwd . --execute --autonomy agent --task "<research objective>" --json
```

CLI preview:

```text
comx-agent run builtin:research-brief --task "<research objective>" --cwd . --dry-run
```

## Expected behavior

- Uses a Codex search/research lane.
- Writes a source-backed brief under `.comx-agent/runs/research-brief/`.
- Separates evidence, inference, confidence, uncertainty, and follow-up questions.

## Output interpretation

Use the result to decide one of:

- enough evidence -> `idea-to-prd`
- still ambiguous -> `discovery-gate` or OMX deep-interview handoff
- not worth building -> stop/no-build decision
- large build remains valuable -> `company-run`
