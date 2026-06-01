---
name: omx-agent-release-readiness
description: Use when the user mentions release-readiness or needs final verification, docs/run-ledger checks, Alexandria memory closeout, release summary, and an honest release/no-release decision.
---

# omx-agent release-readiness

Use `builtin:release-readiness` as the final release decision after review-gate is clean.

## When to use

- Review-gate approved the change.
- You need final verification commands and artifact checks.
- You need docs/run-ledger closeout.
- You need Alexandria MCP memory closeout.

## Do not use

- Before implementation/review evidence exists.
- To hide missing tests or unresolved blockers.
- As a substitute for `review-gate`.

## Standard usage

```bash
agent-remote commands show builtin:release-readiness --cwd . --json
agent-remote run builtin:release-readiness --cwd . --dry-run --task "<release candidate or artifact root>" --json
agent-remote run builtin:release-readiness --cwd . --execute --autonomy agent --task "<release candidate or artifact root>" --json
```

Development fallback:

```bash
PYTHONPATH=src:src/omx_remote uv run python omx_agent_adapter_cli.py run builtin:release-readiness --cwd . --execute --autonomy agent --task "<release candidate or artifact root>" --json
```

TUI preview:

```text
/run builtin:release-readiness --task "<release candidate or artifact root>"
```

## Expected behavior

- Verifies final release readiness.
- Checks docs and run ledger needs.
- Uses Alexandria MCP tools for curated memory closeout when available.
- Produces release summary and release/no-release verdict.

## Output interpretation

Only claim release when verification, review evidence, documentation expectations, and memory closeout are complete. Otherwise report exact blockers and next command.
