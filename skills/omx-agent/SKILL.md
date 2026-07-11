---
name: omx-agent
description: Use when working with this repo's comx-agent adapter commands, routes, repo subagents, or Codex/OMX workflow previews.
---

# omx-agent

Use this single repo skill as a pointer to the adapter's command catalog. Do not
mirror every command in separate skills.

## First move

```bash
comx-agent commands list --cwd . --json
comx-agent commands show builtin:<command> --cwd . --json
comx-agent run builtin:<command> --cwd . --dry-run --task "<task>" --json
```

## Public workflow commands

- `route-next`: classify the safest next command.
- `discovery-gate`: clarify ambiguity, no-build, reroute, or company-run fit.
- `research-brief`: produce source-backed evidence before planning.
- `idea-to-prd`: write PRD/test/execution artifacts.
- `implementation-kickoff`: approve a development handoff.
- `team-sync`: read Team progress without mutation.
- `integration-plan`: merge worker outputs safely.
- `review-gate`: approve/block implementation evidence.
- `release-readiness`: final closeout decision.
- `company-run`: expensive macro loop only when discovery justifies it.

Maintenance lives under `adapter-ops <subcommand>` and is not part of the ten
public workflow commands.

## Rules

- Prefer the smallest command that solves the task.
- Use `--dry-run` before mutation or runtime launch.
- Treat Team output as evidence, not release readiness.
- Keep final claims tied to tests, artifacts, and run records.
