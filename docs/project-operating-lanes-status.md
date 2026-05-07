# Project Operating Lanes Status

## Current project definition

`agent-remote` exists to help agents use **OMX + Codex strongly**. It should make agent operation safer and more capable through typed contracts, route guidance, evidence collection, runtime guardrails, and durable lifecycle artifacts.

It is not a replacement for OMX, Codex, Ralph, Team, or Ultrawork.

Documentation retention policy lives in `docs/README.md`. In short: commit durable status/operating/rules docs; keep local backlog and historical implementation plans under gitignored `docs/jobs/` unless explicitly requested.

## Status labels

| Label | Meaning |
| --- | --- |
| Implemented baseline | A usable, tested baseline exists. Dogfood can still improve it. |
| Partial | Important contracts or helpers exist, but the route is not complete end-to-end. |
| Planned | Concept/scaffold only. Do not claim runtime capability. |
| Deprecated / remove | Current surface is misleading or obsolete and should be removed/replaced. |
| Local planning | Exists under `docs/jobs/`, which is gitignored local planning space. |

## Six operating lanes

| # | Lane | Status | Developed pieces | Missing / next correction |
| --- | --- | --- | --- | --- |
| 1 | Goal only | Implemented baseline | `agent-remote goal start`, `goal status`, `goal template`, adapter-owned Goal mirror state, tests around native Goal startup/status/template. | Continue dogfood; do not add automatic route selection or `goal draft` without review. |
| 2 | Goal → Ralph | Partial, usable by handoff | `agent-remote goal prepare-ralph`, typed Goal mirror/handoff prompt, Ralph PRD artifact contract, Ralph launch/resume/cleanup guardrails. | `agent-remote goal launch-ralph` is deprecated/misleading because it creates a narrow PRD helper and can bypass the intended lane semantics. Remove or replace with a proper reviewed handoff/operating-loop surface. |
| 3 | Goal → Ralph → Team(s) | Partial, not end-to-end complete | Goal/Ralph handoff prompt, Ralph PRD Team fanout fields, Team worker assignments, Team Admin policy, Team Admin aggregation report contract, Ralph post-Team review, Goal lifecycle decision/restore/operating-decision contracts. | One coherent CLI/lifecycle path, Team worker startup/readiness evidence, Team Admin aggregation command, Ralph post-Team review command, Goal lifecycle decision command, full dogfood proof. |
| 4 | Ultrawork only | Implemented baseline | `agent-remote ultrawork launch`, `ultrawork resume`, `ultrawork cleanup-stale`, state preflight, stale/resumable/terminal guards. | Keep dogfooding; improve only from concrete OMX evidence. |
| 5 | Hypergoal | Planned only | `agent-remote hypergoal template` static scaffold. | No executor, runtime state, lifecycle loop, or auto orchestration yet. Do not claim more than planning/template support. |
| 6 | Ralph → Team | Partial, Ralph-owned fanout | Ralph PRD `requires_team_fanout` validation, `team_worker_assignments`, `team_admin`, Ralph Team DAG/handoff artifact helpers, guarded Team launch path. | Clean live proof without Goal wrapping, better Team launch readiness/status UX, aggregation handoff evidence. |

## Deprecated or misleading surfaces

| Surface | Status | Reason | Action |
| --- | --- | --- | --- |
| `agent-remote goal launch-ralph` | Deprecated / remove or replace | It was added as a narrow Goal→Ralph PRD review/launch helper and does not represent the full Goal→Ralph or Goal→Ralph→Team operating lanes. It also risks implying that Goal directly controls launch semantics instead of using the evidence-first operating loop. | Remove in the next code cleanup, or replace with a reviewed handoff command whose name and output make the limited scope explicit. |
| Treating `Ralph → Team` as only an implementation detail | Deprecated wording | The current product definition recognizes `Ralph → Team` as its own Ralph-owned operating lane, separate from Goal-supervised `Goal → Ralph → Team(s)`. | Keep both lanes in docs/help/status tables. |
| `Goal → Ultrawork` as a route label | Deprecated wording | Hypergoal is the planned concept for long Goal + Ultrawork-style work; `Goal → Ultrawork` should not appear as a current route. | Use `Hypergoal` and mark it planned only. |
| `agent-remote` as only a type-safe OMX wrapper | Deprecated wording | The project definition changed to helping agents use OMX + Codex strongly, not just wrapping commands. | Prefer “agent-facing control layer for OMX + Codex.” |

## Folder-level documentation status

| Folder / doc area | Status | Notes |
| --- | --- | --- |
| `README.md` | Updated | Now states the current OMX + Codex project definition and six-lane status table. |
| `AGENTS.md` | Updated | Now tells future agents the six lanes and the current project positioning. |
| `docs/README.md` | New source-of-truth policy | Explains what docs belong in git, what stays local, and how to mark done/deferred/deprecated work. |
| `docs/agent-remote-goal-operating-loop.md` | Updated | Now uses the six-lane map and marks partial/planned/deprecated pieces. |
| `docs/project-operating-lanes-status.md` | New source-of-truth summary | This document is the quick status index for route/lane claims. |
| `docs/future-runtime-readiness.md` | Current enough | Still useful as runtime-expansion guardrails; it should not override the OMX + Codex product definition. |
| `docs/rules/` | Current enough | These are development rules, not roadmap status docs. Keep them stable unless code conventions change. |
| `docs/jobs/` | Local planning, gitignored | Update for local handoff/status, but do not treat as push-bound documentation unless explicitly requested. |

## What counts as “done” for each lane

A lane is not done because a prompt or schema exists. It is done when the route has:

1. typed request/state/output contracts,
2. CLI or library surface agents can actually use,
3. read-only evidence guidance before mutation,
4. guardrails for stale/resumable/active runtime state,
5. tests for contract and CLI behavior,
6. at least one real dogfood proof for runtime paths that claim execution.

## Immediate next documentation/code cleanup

1. Remove or replace `agent-remote goal launch-ralph` so it does not misrepresent Goal→Ralph or Goal→Ralph→Team.
2. Add explicit CLI/status surfaces for the missing Goal→Ralph→Team steps instead of adding another broad launcher.
3. Keep Hypergoal as planned/template-only until dogfood proves a deeper lifecycle is needed.
4. Preserve `Ralph → Team` as a separate lane in docs and help text.
