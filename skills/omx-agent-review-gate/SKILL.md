---
name: omx-agent-review-gate
description: Use when the user mentions review-gate or needs code, security, architecture, QA, test, or release-blocker review lanes with an approve/block decision before release.
---

# omx-agent review-gate

Use `builtin:review-gate` as the quality gate before release readiness or final completion claims.

## When to use

- Implementation or integration is complete enough for review.
- You need code/security/architecture/QA review evidence.
- Company-run reaches review loop.
- You need an approve/block verdict and required fixes.

## Do not use

- Before implementation evidence exists.
- As a rubber stamp without reading artifacts/tests.
- To claim release readiness; use `release-readiness` after approval.

## Standard usage

```bash
agent-remote commands show builtin:review-gate --cwd . --json
agent-remote run builtin:review-gate --cwd . --dry-run --task "<change set or artifact root>" --json
agent-remote run builtin:review-gate --cwd . --execute --autonomy agent --task "<change set or artifact root>" --json
```

Development fallback:

```bash
PYTHONPATH=src:src/omx_remote uv run python omx_agent_adapter_cli.py run builtin:review-gate --cwd . --execute --autonomy agent --task "<change set or artifact root>" --json
```

CLI preview:

```text
comx-agent run builtin:review-gate --task "<change set or artifact root>" --cwd . --dry-run
```

## Expected behavior

- Runs specialist review lanes.
- Produces code, security, architecture, and QA/test findings.
- Emits approve/block/watch verdict with evidence.

## Output interpretation

`approve` means proceed to `release-readiness`. `block` or material `watch` means return to implementation/integration and rerun review after fixes.
