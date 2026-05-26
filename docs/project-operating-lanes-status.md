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
| 2 | Goal → Ralph | Partial, usable by handoff | `agent-remote goal prepare-ralph`, typed Goal mirror/handoff prompt, Ralph PRD artifact contract, Ralph launch/resume/cleanup guardrails. The misleading public `agent-remote goal launch-ralph` command has been removed. | Keep Goal→Ralph as read-only handoff plus Ralph-owned control; add no new broad launcher without dogfood evidence. |
| 3 | Goal → Ralph → Team(s) | Implemented baseline, dogfood-proven with follow-up wave | Goal/Ralph handoff prompt, Ralph PRD Team fanout fields, Team worker assignments, Team Admin policy, Team Admin aggregation report/read command with `proof_layers`, Ralph post-Team review command, Goal lifecycle decision/restore/operating-decision contracts, Ralph-owned Team launch handoff, worker allocation hint cleanup, and startup readiness issue surfacing through `startup_issue_workers`. | Continue dogfood. Remaining hardening is mostly native OMX worker startup reliability: `ready_prompt_timeout` forensics, pane relaunch, and same-assignment redispatch. Keep treating startup failures as `worker_readiness` proof-layer evidence rather than ambiguous completion. |
| 4 | Ultrawork only | Implemented baseline | `agent-remote ultrawork launch`, `ultrawork resume`, `ultrawork cleanup-stale`, state preflight, stale/resumable/terminal guards. | Keep dogfooding; improve only from concrete OMX evidence. |
| 5 | UltraGoal | Native OMX + composition baseline | `agent-remote ultragoal status` exposes native OMX UltraGoal capability/status evidence. Command recipes, route policy, cockpit capability evidence, `agent-remote next`, run records, and upstream probes now make UltraGoal-oriented composition inspectable before launch. | Keep actual durable roadmap execution in native OMX UltraGoal. Do not claim adapter-owned non-dry-run roadmap automation until it has explicit execution, replay, and dogfood evidence. |
| 6 | Ralph → Team | Implemented baseline for handoff and review surfaces | Ralph PRD `requires_team_fanout` validation, `team_worker_assignments`, `team_admin`, Ralph Team DAG/handoff artifact helpers, guarded Team launch path, Team Admin aggregation with proof layers, Ralph post-Team review, and startup issue follow-up classification. | Clean single-wave live proof still depends on native OMX worker startup reliability. Add deeper runtime reconnect only in OMX, not as adapter-owned pane control. |

## Deprecated or misleading surfaces

| Surface | Status | Reason | Action |
| --- | --- | --- | --- |
| `agent-remote goal launch-ralph` | Removed public surface | It was added as a narrow Goal→Ralph PRD review/launch helper and did not represent the full Goal→Ralph or Goal→Ralph→Team operating lanes. It also risked implying that Goal directly controls launch semantics instead of using the evidence-first operating loop. | Keep removed; use `goal prepare-ralph` plus `agent-remote ralph ...` until a better reviewed handoff surface is proven. |
| Treating `Ralph → Team` as only an implementation detail | Deprecated wording | The current product definition recognizes `Ralph → Team` as its own Ralph-owned operating lane, separate from Goal-supervised `Goal → Ralph → Team(s)`. | Keep both lanes in docs/help/status tables. |
| `Goal → Ultrawork` as a route label | Deprecated wording | Durable long-roadmap work should use native OMX UltraGoal or a future project-owned command recipe, not a Goal→Ultrawork label. | Use `UltraGoal` when the native durable multi-goal workflow is intended. |
| `agent-remote` as only a type-safe OMX wrapper | Deprecated wording | The project definition changed to helping agents use OMX + Codex strongly, not just wrapping commands. | Prefer “agent-facing control layer for OMX + Codex.” |
| Project-owned `HyperGoal` lane or command | Removed public surface | OMX now owns durable multi-goal execution as native UltraGoal, while adapter-owned composition is generalized under recipes, route recommendations, preflight, and run records. | Use `agent-remote ultragoal status` for native UltraGoal evidence and `agent-remote commands` / `agent-remote run --dry-run` for project-owned composition. |

## Folder-level documentation status

| Folder / doc area | Status | Notes |
| --- | --- | --- |
| `README.md` | Updated | Now states the current OMX + Codex project definition and six-lane status table. |
| `AGENTS.md` | Updated | Now tells future agents the six lanes and the current project positioning. |
| `docs/README.md` | New source-of-truth policy | Explains what docs belong in git, what stays local, and how to mark done/deferred/deprecated work. |
| `docs/agent-remote-goal-operating-loop.md` | Updated | Now uses the six-lane map and marks partial/planned/deprecated pieces. |
| `docs/project-operating-lanes-status.md` | New source-of-truth summary | This document is the quick status index for route/lane claims. |
| `docs/examples/` | New operator and agent examples | Documents command recipes, route recommendations, run records, TOML subagents, and native UltraGoal JSON surfaces. JSON fenced blocks are parsed by tests to reduce stale examples. |
| `docs/native-omx-worker-startup-reliability.md` | New native-bound reliability plan | Captures adapter-compatible evidence expectations for `ready_prompt_timeout`, relaunch/retry, and same-assignment redispatch while keeping pane lifecycle mutation in native OMX. |
| `docs/future-runtime-readiness.md` | Current enough | Still useful as runtime-expansion guardrails; it should not override the OMX + Codex product definition. |
| `docs/rules/` | Current enough | These are development rules, not roadmap status docs. Keep them stable unless code conventions change. |
| `docs/jobs/` | Local planning, gitignored | Update for local handoff/status, but do not treat as push-bound documentation unless explicitly requested. |

## 2026-05-08 Goal/Ralph/Team dogfood proof

A live Goal-supervised Ralph→Team run closed the baseline loop through a follow-up wave:

- Goal: `goal-decf39b42eff`
- Team: `dogfood-the-goal-to-r-861e14ef`
- Follow-up Team: `follow-up-the-documen-861e14ef`
- Final Ralph review: `complete`
- Final Goal lifecycle decision: `close_goal`
- Final operating decision: `current_stage=goal_close_ready`, `safe_to_mutate=true`, `missing_evidence=[]`

The first Team wave proved worker assignment/DAG ownership and surfaced a native OMX/Codex startup reliability gap: `worker-3` reached pane/identity setup but failed ready-prompt detection with `ready_prompt_timeout`. The adapter now preserves that as explicit `startup_issue_workers` and `worker_readiness` proof-layer evidence in Team Admin aggregation, cockpit decision reasons, and Ralph post-Team review, so follow-up work is classified deliberately instead of being hidden as ambiguous missing/pending state.

## What counts as “done” for each lane

A lane is not done because a prompt or schema exists. It is done when the route has:

1. typed request/state/output contracts,
2. CLI or library surface agents can actually use,
3. read-only evidence guidance before mutation,
4. guardrails for stale/resumable/active runtime state,
5. tests for contract and CLI behavior,
6. at least one real dogfood proof for runtime paths that claim execution.

## Immediate next documentation/code cleanup

Detailed current feature scope lives in `docs/current-feature-development-scope.md`.

1. Dogfood Team proof-layer output in live Team waves so agents can distinguish DAG/import/assignment success from Codex worker readiness, dispatch, and completion evidence.
2. Add native OMX runtime hardening for worker startup reliability outside the adapter: timeout forensics, worker pane relaunch, and same-assignment redispatch.
3. Use `agent-remote next` for read-only cross-lane recommendation before any mutation, then keep command composition evidence-first: route recommendation → preflight → dry-run plan → optional run record/handoff before any native mutation.
4. Keep the Pydantic dependency posture stable unless a concrete TypedDict hardening slice requires a tighter minimum; if PEP 728 `TypedDict` features are adopted, use `typing_extensions.TypedDict` rather than stdlib `typing.TypedDict`.
5. Keep UltraGoal mapped to native OMX and put project-owned composition behavior under command recipes rather than reviving HyperGoal.
6. Preserve `Ralph → Team` as a separate lane in docs and help text.
