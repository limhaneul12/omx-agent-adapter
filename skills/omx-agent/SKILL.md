---
name: omx-agent
description: Use when operating or explaining this repository's current comx-agent Codex/OMX ADE, nine lifecycle CLI operations, Recipes, Run evidence, cancellation, native resume, or cross-provider handoff; also use when replacing guidance that still mentions removed agent-remote, workflow catalogs, or the old TUI.
---

# comx-agent

Operate the native ADE and thin controller-neutral execution core. Do not revive
the removed workflow engine, command catalog, `agent-remote`, `omx_remote`, or
curses TUI.

## Choose the surface

- Human Project/Workspace/Run navigation: `uv run comx-agent ade --cwd .`
- Automation and diagnostics: `comx-agent` CLI
- Trusted controller or Hermes: typed `HarnessTools`

Read `docs/usage-guide.ko.md` when the user needs complete interactive or CLI
instructions. Read `GOAL.md` before changing product boundaries.

## Standard flow

1. Discover actual provider support.
2. Preview the exact typed Plan.
3. Execute with an idempotency key when retry safety matters.
4. Inspect status, events, and verified Artifacts.
5. Cancel, resume, or cross-provider handoff only through the existing lifecycle
   operation.

```bash
uv run comx-agent capabilities

uv run comx-agent plan \
  --provider codex \
  --cwd . \
  --idempotency-key review-01 \
  "Inspect without modifying files."

uv run comx-agent run \
  --provider codex \
  --cwd . \
  --idempotency-key review-01 \
  "Inspect without modifying files."

uv run comx-agent status RUN_ID --cwd .
uv run comx-agent events RUN_ID --cwd .
uv run comx-agent artifacts RUN_ID --cwd .
```

## ADE Recipes

- `Quick Review`: Codex, read-only evidence-backed review.
- `Implement Safely`: Codex, explicit workspace write with on-request approval.
- `Implement and Verify`: Codex write plus required `verification.md`.
- `OMX Goal Execution`: native OMX execution with explicit workspace write.

In the ADE, enter a multiline Objective, select a Recipe, review the exact Plan,
then start the detached Run. Closing the ADE does not cancel the Run.

## Lifecycle controls

```bash
uv run comx-agent cancel RUN_ID --cwd .

uv run comx-agent resume RUN_ID \
  --cwd . \
  --idempotency-key resume-RUN_ID-01 \
  --objective "Continue from native session evidence."

uv run comx-agent handoff SOURCE_RUN_ID \
  --target-provider omx \
  --cwd . \
  --idempotency-key handoff-SOURCE_RUN_ID-omx-01 \
  "Independently verify the source result."
```

Resume must fail when the native session ID or provider capability is missing.
Handoff must preserve source provenance and use a different provider.

## Safety and evidence

- Prefer the smallest command that solves the task.
- Read-only is the default.
- Mutation requires both explicit controller intent and a non-read-only sandbox.
- A zero exit code is not semantic success.
- Required result, Plan, and declared Artifacts must exist and be non-empty.
- Treat provider topology and tmux identity as unknown unless native evidence
  reports them.
- OMX owns Team, Ralph, UltraGoal, missions, and capability locks.
- Run truth lives in the Workspace `.comx-agent/v2` store; ADE view state does
  not change Run truth.

## Verification

For repository changes, run:

```bash
make ruff
make pyrefly
make test
make ci
make native-test
```

Do not claim completion from a command exit alone. Report tests, verified
Artifacts, remaining external blockers, and whether any commit or push occurred.
