# Agent Remote Goal Operating Loop

## Purpose

`agent-remote` is an adapter/cockpit for operating OMX, not a replacement runtime. The Goal/Ralph/Team harness should help an agent decide **when to inspect, when to review, and when it is safe to mutate** while keeping OMX/Ralph/Team artifacts as the source of truth.

Use this loop when continuing a Goal/Ralph/Team task or deciding the next OMX action from durable lifecycle state.

## Default Loop

```text
1. Restore durable Goal lifecycle state.
2. Ask agent-remote for the operating decision.
3. Execute read-only recommended evidence commands first.
4. Build the next adapter-owned derived artifact only after evidence is present.
5. Re-run operating-decision before any mutation or close/follow-up action.
6. Stop for review when requires_review=true or safe_to_mutate=false and no evidence command remains.
```

## Commands

### 1. Restore lifecycle state

```bash
PYTHONPATH="$PWD/src:$PWD" uv run agent-remote goal restore-lifecycle \
  --goal-id <goal-id> \
  --cwd .
```

Use source-first `PYTHONPATH` during local development so the console entrypoint sees the current working tree instead of an older installed wheel. After install/push hygiene is settled, plain `uv run agent-remote ...` is enough.

### 2. Read the operating decision

```bash
PYTHONPATH="$PWD/src:$PWD" uv run agent-remote goal operating-decision \
  --goal-id <goal-id> \
  --team-name <team-name> \
  --cwd .
```

Important output fields:

| Field | Meaning |
| --- | --- |
| `current_stage` | Derived control stage from restored lifecycle state. |
| `next_action` | Recommended agent action. |
| `safe_to_mutate` | Whether the next action may mutate Goal/OMX state without more evidence. |
| `requires_review` | Whether execution should stop for human/reviewer input. |
| `available_evidence` | Evidence already present in durable artifacts. |
| `missing_evidence` | Required evidence not yet present. |
| `recommended_commands` | Read-only OMX commands to run before the next derived decision. |
| `review_blockers` | Known blockers from lifecycle/review artifacts. |

### 3. Execute recommended read-only OMX commands

If `missing_evidence` contains Team API sources, run the commands from `recommended_commands` before deriving Team Admin aggregation or review decisions.

Common examples:

```bash
omx team api list-tasks --input '{"team_name":"<team-name>"}' --json
omx team api read-events --input '{"team_name":"<team-name>"}' --json
omx team api read-worker-status --input '{"team_name":"<team-name>","worker":"worker-1"}' --json
```

A missing or not-yet-launched team can still return stable read-only evidence. For example, empty tasks/events and `unknown` worker states are valid evidence that the agent should not pretend a Team wave has completed.

## Stage Guide

| `current_stage` | Meaning | Normal next move |
| --- | --- | --- |
| `team_admin_aggregation_pending` | Team Admin report is not present yet. | Run read-only Team API evidence commands, then build aggregation. |
| `ralph_post_team_review_pending` | Aggregation exists; Ralph review does not. | Run Ralph post-Team review against the PRD and aggregation report. |
| `goal_lifecycle_decision_pending` | Ralph review exists; Goal lifecycle decision does not. | Build lifecycle decision. |
| `goal_close_ready` | Lifecycle says close is safe. | Mutation may proceed if no external policy blocks it. |
| `ralph_follow_up_ready` | Follow-up worker wave is needed. | Prepare next Ralph/Team handoff; do not silently close. |
| `human_review_required` | Human/reviewer gate is required. | Stop and surface blockers. |

## Objective Pruning Rules

The harness should stay small. Use these rules before adding more features:

1. Prefer read-only evidence and typed summaries over new state writers.
2. Do not make `agent-remote` own Team execution or replace OMX/Ralph.
3. Do not add a CLI command unless it exposes an already-useful library surface.
4. Remove or shrink fields that are not used in real dogfood after 2-3 feature runs.
5. Treat `recommended_commands` as hints, not an execution engine.
6. Keep mutation gated by `safe_to_mutate`, `requires_review`, and lifecycle artifacts.

## Current Keep/Delete Assessment

| Surface | Keep now? | Reason |
| --- | --- | --- |
| `restore-lifecycle` CLI | Keep | Needed for resume/session handoff and dogfood. |
| `operating-decision` CLI | Keep | Thin surface over existing runtime; useful for dogfood. |
| `recommended_commands` | Keep experimentally | It successfully nudges agents toward OMX read-only evidence first. |
| `CodexGoalOperatingStage` | Keep experimentally | More readable than raw resume targets, but review after real use. |
| `safe_to_mutate` / `requires_review` | Keep | Directly prevents unsafe close/follow-up behavior. |
| Extra write/mutation CLIs | Do not add yet | Would make adapter look like a replacement runtime. |
| Local dogfood artifacts | Delete after use | They are runtime scratch, not source truth. |

## Verification Checklist

Before considering the loop healthy for a feature run:

- [ ] `agent-remote goal restore-lifecycle` returns `ready_to_resume=true`.
- [ ] `agent-remote goal operating-decision` returns a clear `current_stage` and `next_action`.
- [ ] If `safe_to_mutate=false`, the agent runs read-only `recommended_commands` first.
- [ ] Empty/unknown Team API evidence is treated honestly, not as success.
- [ ] Derived Team Admin/Ralph/Goal artifacts are rebuilt only after evidence is gathered.
- [ ] Full repo gates pass before commit.
- [ ] Local `.agent-remote/` dogfood artifacts are cleaned up unless intentionally needed for live continuation.
