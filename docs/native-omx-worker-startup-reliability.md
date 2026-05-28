# Native OMX Worker Startup Reliability Plan

Last updated: 2026-05-25 KST

This document records the adapter-side evidence contract for native OMX Team worker
startup hardening. It is intentionally a plan and compatibility contract, not an
`agent-remote` pane-control design.

## Boundary

`agent-remote` may read and summarize startup evidence. Native OMX owns all
runtime mutation:

- tmux pane lifecycle and relaunch;
- ready-prompt detection and retry timing;
- worker reconnect/relaunch policy;
- same-assignment redispatch;
- final worker health transitions.

The adapter must not launch replacement panes, duplicate task claims, redispatch
worker assignments, or treat a native API `ok: true` as worker completion.

## Evidence layers

Team/Ralph status should remain split into these proof layers:

1. `prd_dag_import` — Ralph PRD, Team DAG, manifest/import, and Team Admin policy
   evidence exists.
2. `assignment` — worker IDs, task ownership, and intended assignment mapping are
   known.
3. `worker_readiness` — Codex worker process/session readiness is proven, partial,
   or failed.
4. `dispatch` — task dispatch, mailbox/inbox delivery, hook receipt, and event
   stream evidence exists.
5. `completion` — worker handoff/completion evidence is merge-ready or still
   incomplete.

`ready_prompt_timeout`, `startup_prompt_timeout`, and `worker_startup_timeout`
belong to `worker_readiness`. They must not be collapsed into generic missing
worker output or inferred completion.

## Forensic checklist before native cleanup

Use read-only probes and preserve evidence before cleanup or relaunch:

- team name and worker ID;
- `.omx/state/team/<team>/startup-timing.json` when available;
- `.omx/logs/team-delivery-*.jsonl` entries for startup and dispatch phases;
- tmux pane IDs and commands;
- worker cwd;
- identity inbox path/content;
- Codex session metadata path/content;
- hook receipt events;
- task owner and claim-owner mapping;
- `omx team status <team> --json`;
- `omx team api list-tasks --input ... --json`;
- `omx team api read-events --input ... --json`;
- `omx team api read-worker-status --input ... --json`.

All probes should be bounded and read-only.

## Native OMX retry policy proposal

Native OMX should implement any retry/relaunch behavior behind its own Team
runtime boundary:

1. Retry at most once by default when a worker times out before task dispatch.
2. Preserve the same worker ID and task assignment across relaunch.
3. Do not create two active panes for the same worker.
4. Do not duplicate task claims or mutate DAG/import ownership.
5. If relaunch succeeds, emit a recovered startup event with the original worker
   ID, replacement pane/session evidence, and assignment ID.
6. If relaunch fails, keep an unresolved startup issue state and preserve the
   original timeout evidence.
7. If every worker fails readiness, fail or stop the Team wave with a precise
   fatal startup status.

## Adapter compatibility expectations

The adapter currently supports timeout-only evidence through
`startup_issue_workers` and Team proof layers. Future native OMX JSON can add
recovered-startup evidence without breaking older adapter behavior if it exposes:

- worker ID;
- original timeout event type;
- retry attempt count;
- recovered/unrecovered state;
- original and replacement pane/session IDs when applicable;
- preserved task/assignment ID;
- dispatch status after recovery.

Until native OMX exposes recovered startup semantics, the adapter should continue
to classify startup timeout workers as blocking `worker_readiness` evidence and
recommend inspection/follow-up rather than mutation.

## Adapter smoke after native OMX changes

After native OMX implements recovery or richer startup status, validate the
adapter compatibility with:

```bash
PYTHONPATH="$PWD/src:$PWD" uv run agent-remote cockpit snapshot --cwd . --team <team> --json
PYTHONPATH="$PWD/src:$PWD" uv run agent-remote team admin-report --team <team> --prd-path <typed-prd.json>
```

Success means the adapter can distinguish recovered startup, unresolved startup
issue, dispatch evidence, and completion evidence without owning any pane
lifecycle mutation.
