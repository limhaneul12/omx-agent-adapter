---
name: omx-agent-company-run
description: Use when the user mentions company-run or wants a build-oriented company-style operating loop with discovery/ROI gates, CEO/orchestrator, councils, voting, PRD, Team/subagents, implementation kickoff, review, release, and Alexandria memory closeout.
---

# omx-agent company-run

Use `builtin:company-run` for substantial build-oriented work that deserves a company-style operating loop. It is not the default for tiny tasks.

## When to use

- The user gives a product/feature goal that may require research, planning, Team, implementation, review, and release readiness.
- Discovery-gate says `ready-for-company-run`.
- The task benefits from CEO/orchestrator, Research Council, Product/PRD Council, Executive Council, and OMX Team lanes.
- You need durable artifacts and internal decisions rather than a one-agent report.

## Do not use

- For tiny changes that `route-next`, `research-brief`, or `idea-to-prd` can handle.
- From a dirty worktree if live Team fanout is expected.
- To skip discovery, PRD, test spec, or executive readiness gates.
- To claim release when status is `requires_agent_action`.

## Standard usage

```bash
agent-remote commands show builtin:company-run --cwd . --json
agent-remote run builtin:company-run --cwd . --dry-run --task "<idea or build goal>" --json
agent-remote run builtin:company-run --cwd . --execute --autonomy agent --task "<idea or build goal>" --json
```

For live Team handoff when the worktree is clean:

```bash
agent-remote run builtin:company-run --cwd . --execute --autonomy agent --live-team --worker-count 4 --model gpt-5.5 --xhigh --task "<idea or build goal>" --json
```

Development fallback:

```bash
PYTHONPATH=src:src/omx_remote uv run python omx_agent_adapter_cli.py run builtin:company-run --cwd . --execute --autonomy agent --task "<idea or build goal>" --json
```

TUI preview:

```text
/run builtin:company-run --task "<idea or build goal>"
```

## Required lifecycle

1. memory/context recovery
2. discovery-gate and ROI/no-build decision
3. research council and research sufficiency decision
4. proceed/no-build/orchestrator decision
5. PRD, test spec, execution brief
6. executive readiness gate
7. implementation-kickoff
8. Team/subagent implementation lanes
9. team-sync and integration-plan loops
10. review-gate loop
11. release-readiness and Alexandria memory closeout

## Output interpretation

`requires_agent_action` is a safe handoff, not a completed build. If Team launch is blocked by dirty worktree, commit/stash/create a clean worktree before live Team fanout.
