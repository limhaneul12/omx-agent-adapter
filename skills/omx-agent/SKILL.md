---
name: omx-agent
description: Use when an agent must operate or explain the comx-agent Codex/OMX ADE, inspect Project/Workspace/Worktree/Attention context, use the nine Run lifecycle operations, or replace guidance that mentions removed agent-remote, omx_remote, workflow catalogs, or the curses TUI.
---

# comx-agent

Operate the Codex/OMX ADE through typed application and Run lifecycle surfaces. Do not automate GUI widgets when a JSON command or Python method exists. Do not revive `agent-remote`, `omx_remote`, the removed workflow engine, or the curses prototype.

## Choose the surface

- Human interactive operation: `uv run comx-agent ade --cwd .`
- Agent application context and Workspace actions: `comx-agent agent ...`
- Run lifecycle automation: top-level `comx-agent` lifecycle commands
- Trusted Python controller: `AdeAgentTools` plus `HarnessTools`

Read `GOAL.md` before changing product boundaries and `docs/usage-guide.ko.md` for complete operation guidance.

## Agent-first flow

1. Read one platform context snapshot.
2. Register the Project if absent.
3. Select, adopt, or create the correct Workspace or Worktree.
4. Re-read context and use the returned Workspace path.
5. Discover provider capabilities.
6. Plan before execution.
7. Run with an idempotency key when retry safety matters.
8. Inspect status, events, Artifacts, and Attention.
9. Cancel, resume, or handoff only through supported lifecycle operations.

```bash
uv run comx-agent agent context

uv run comx-agent agent register-project /absolute/project/path

uv run comx-agent agent discover-worktrees PROJECT_ID

uv run comx-agent agent create-worktree \
  PROJECT_ID agent/safe-change

uv run comx-agent agent inspect-workspace WORKSPACE_ID
```

`agent context` is the preferred discovery entry point. It returns strict JSON containing the ADE catalog, active presentation selection, provider capability report, Recipes, live Workspace status, recent Runs, and evidence-based Attention count. Missing provider facts remain `null` with an explicit error; they are never invented.

## Run lifecycle flow

```bash
uv run comx-agent capabilities

uv run comx-agent plan \
  --provider codex \
  --cwd WORKSPACE_PATH \
  --idempotency-key review-01 \
  "Inspect without modifying files."

uv run comx-agent run \
  --provider codex \
  --cwd WORKSPACE_PATH \
  --idempotency-key review-01 \
  "Inspect without modifying files."

uv run comx-agent status RUN_ID --cwd WORKSPACE_PATH
uv run comx-agent events RUN_ID --cwd WORKSPACE_PATH
uv run comx-agent artifacts RUN_ID --cwd WORKSPACE_PATH
```

Never derive a Workspace path from naming conventions when `agent context`, `discover-worktrees`, or `inspect-workspace` can return canonical identity.

## Detached agent operation

Use a detached operation when the caller must regain control immediately, operate multiple Workspaces, or let work survive the launching process. Write a strict `DetachedOperationRequest` JSON file:

```json
{
  "operation": "run",
  "request": {
    "controller_id": "trusted-agent",
    "provider": "codex",
    "objective": "Inspect without modifying files.",
    "workspace": "/absolute/workspace/path",
    "idempotency_key": "agent-review-01"
  }
}
```

```bash
uv run comx-agent agent start-operation operation.json
uv run comx-agent agent operation OPERATION_ID
uv run comx-agent agent operations
uv run comx-agent agent context
```

The returned operation ID is ADE worker identity, not Run identity. Poll the operation until it succeeds or fails, then use the Run ID from its result and the normal `status`, `events`, and `artifacts` operations. Do not create an external polling database or scheduler around it.

## Recipes

- `Quick Review`: Codex read-only evidence-backed review.
- `Implement Safely`: Codex explicit Workspace write with on-request approval.
- `Implement and Verify`: Codex write plus required `verification.md`.
- `OMX Goal Execution`: native OMX execution with explicit Workspace write.

Recipes select native behavior. OMX still owns Team, Ralph, UltraGoal, missions, capability locks, worker creation, and task allocation.

## Lifecycle controls

```bash
uv run comx-agent cancel RUN_ID --cwd WORKSPACE_PATH

uv run comx-agent resume RUN_ID \
  --cwd WORKSPACE_PATH \
  --idempotency-key resume-RUN_ID-01 \
  --objective "Continue from native session evidence."

uv run comx-agent handoff SOURCE_RUN_ID \
  --target-provider omx \
  --cwd WORKSPACE_PATH \
  --idempotency-key handoff-SOURCE_RUN_ID-omx-01 \
  "Independently verify the source result."
```

Resume must fail when the native session ID or provider capability is missing. Handoff must preserve source provenance and target a different provider.

## Safety and evidence

- Prefer the smallest command that solves the task.
- Read-only is the default.
- Mutation requires explicit intent and a write sandbox.
- Worktree creation does not grant commit or push.
- A zero exit code is not semantic success.
- Required result, Plan, and declared Artifacts must exist and be non-empty.
- Treat provider topology and tmux identity as unknown unless native evidence reports them.
- Run truth lives in each Workspace `.comx-agent/v2`; ADE catalog and view state do not replace it.
- Never scrape or click the GUI to perform an action available through `AdeAgentTools`, `HarnessTools`, or JSON CLI.

## Verification

For repository changes run:

```bash
make ruff
make pyrefly
make test
make ci
make native-test
```

Do not claim completion from a command exit alone. Report tests, verified Artifacts, remaining external blockers, and whether any commit or push occurred.
