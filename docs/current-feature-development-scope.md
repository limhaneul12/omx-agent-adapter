# Current Feature Development Scope

Last updated: 2026-05-10 13:46 KST

This document records the current cockpit/status feature boundary after the cockpit baseline, Team evidence hardening, evidence-backed Team discovery, GitHub PR status, runtime structure split, cockpit decision-reason stitching, and Team proof-layer UX slices.

## Product framing

`agent-remote` is an agent-facing control layer for OMX + Codex. It helps agents operate repo-scoped OMX/Codex flows through typed contracts, status observation, evidence collection, guardrails, and lifecycle decisions.

It should not replace OMX, Codex, Ralph, Team, or Ultrawork.

## Completed cockpit baseline

Merged scope:

- PR #5: `feat: expose cockpit all-status sources`
- PR #6: `feat: harden cockpit team evidence actions`

The cockpit baseline now includes:

1. **Repo cockpit snapshot baseline**
   - `agent-remote cockpit snapshot --cwd <repo>` shows the six operating lanes in one read-only repo snapshot.
   - It surfaces contradictions, `safe_to_mutate`, and a recommended next action.
   - It remains read-only: no launch, cleanup, mutation, or implicit advance.

2. **Cockpit all-status source exposure**
   - Snapshot output includes `status_sources`, `discovered_teams`, and top-level `warnings`.
   - The status-source rows distinguish skipped, observed, missing, failed, and unknown evidence.
   - Malformed/unreadable Goal mirror state is surfaced as a failed `goal_mirror_state` source rather than being collapsed into a missing source.

3. **Cockpit Ralph→Team evidence reads**
   - `agent-remote cockpit snapshot --cwd <repo> --team-name <team>` reads real Team status, task, event, and worker-status surfaces.
   - `--team <team>` remains an alias.
   - Read failures degrade into warnings instead of mutating or aborting the whole snapshot.
   - Team reads now appear as a dedicated `team_evidence` status source.

4. **Team evidence mutation-safety hardening**
   - Explicit active Team evidence blocks mutation by setting `safe_to_mutate=false`.
   - Explicit active Team evidence drives top-level `recommended_next_action="inspect_team_evidence"` unless a higher-priority contradiction or active runtime mode is present.
   - `unknown` Team status remains degraded/unknown evidence and is not treated as active runtime evidence.

5. **Evidence-backed Team identity discovery**
   - Cockpit discovers Team names from adapter-owned persisted Goal mirror state when `linked_team_names` contains exact Team identities.
   - A bare `team_worker_count` remains fanout intent only and produces a warning rather than invented Team names.
   - Missing, malformed, or invalid Goal mirror state degrades into empty discovery evidence or warnings without blocking the whole snapshot.

6. **GitHub PR/review/check status source**
   - Cockpit can expose read-only GitHub pull-request evidence for the current branch.
   - The PR source normalizes open/missing/unavailable status, mergeability, review state, and check state while keeping credential handling non-printing and fallback-safe.

7. **Cockpit operating-decision reason stitching**
   - Snapshot output now includes typed `decision_reasons` that explain why `safe_to_mutate` and `recommended_next_action` were chosen.
   - Reasons carry their own `recommended_next_action`, `blocks_mutation`, and evidence `source_names` so future agents do not need to re-derive decisions from scattered status fields.
   - The surface remains evidence-backed and read-only; cockpit still does not launch, cleanup, or implicitly advance runtime state.

8. **Team launch/status proof-layer UX**
   - Team observations now expose typed `proof_layers` so agents can distinguish task owner assignment, worker readiness, dispatch, and completion evidence.
   - The proof layers are read-only classifications over existing Team status/task/event/worker-status surfaces and degrade independently to `missing` or `failed` when a source is unavailable.
   - Lane summary text uses `task_owner_assignment` for the assignment/import layer to avoid overstating DAG/import proof when only task owner evidence is present.

9. **Python support boundary**
   - Project support remains `Python >=3.13,<3.15`.
   - `.python-version` remains on the lower-bound development target.
   - 3.14-only stdlib imports and syntax remain off-limits while Python 3.13 is supported.

## Current verified stopping point

Latest verified cockpit state on `feat/team-proof-layer-status`:

- `git diff --check` passed.
- `uv run ruff check src tests` passed.
- `uv run pyrefly check src` passed with `0 errors`.
- `uv run pytest -q` passed with `749 passed`.
- `uv run agent-remote cockpit snapshot --cwd . --team-name alpha` passed after reinstalling the adapter worktree package with `uv sync --reinstall-package agent-remote`; the missing Team degraded to read-only proof-layer evidence.
- Team observations now include typed `proof_layers` for assignment, readiness, dispatch, and completion evidence.

## Next feature direction

The next work should stay evidence-first and should not broaden cockpit into an automation layer.

Recommended near-term sequence:

1. **Native OMX startup reliability hardening**
   - The adapter should continue surfacing `ready_prompt_timeout` and startup issues as evidence.
   - Actual pane relaunch, same-assignment redispatch, and deeper startup repair belong in native OMX/runtime hardening, not cockpit mutation.

2. **Dependency/transport hardening only when needed**
   - Keep Python support and Pydantic dependency posture stable unless a concrete transport-hardening slice requires a tighter minimum.

3. **Further cockpit UX only from concrete dogfood evidence**
   - Keep cockpit read-only and evidence-first.
   - Add no broad dashboards or automation surfaces without a specific agent-operating decision they improve.

## Explicit non-goals for the next slice

- Do not make Python 3.14-only code the baseline.
- Do not replace Pydantic BaseModel artifact schemas with TypedDicts.
- Do not start a broad Pydantic dependency upgrade as a standalone feature.
- Do not add direct Goal→Team as a public lane.
- Do not make cockpit perform launch, cleanup, or implicit advance.
- Do not treat `unknown` Team evidence as active execution.
- Do not claim Hypergoal runtime support; Hypergoal remains planned/template-only.

## Current dependency decision

Keep the current dependency posture unless a concrete transport-hardening slice requires a tighter minimum:

- Keep Python support at `>=3.13,<3.15`.
- Keep Pydantic v2 as the primary schema/contract layer.
- If PEP 728 TypedDict features are adopted, use `typing_extensions.TypedDict`, not stdlib `typing.TypedDict`.
- If that adoption becomes part of production code, tighten minimums deliberately, for example `pydantic>=2.12,<3.0` and `typing-extensions>=4.15,<5.0`.
