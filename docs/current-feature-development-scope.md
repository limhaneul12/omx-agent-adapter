# Current Feature Development Scope

Last updated: 2026-05-08 17:50 KST

This document records the feature boundary we intended to reach before merging the current cockpit branch back to `main`.

## Product framing

`agent-remote` is an agent-facing control layer for OMX + Codex. It should help agents operate repo-scoped OMX/Codex flows through typed contracts, status observation, evidence collection, guardrails, and lifecycle decisions.

It should not replace OMX, Codex, Ralph, Team, or Ultrawork.

## What this feature branch was meant to deliver

Branch: `feat/agent-remote-cockpit`

The branch was scoped to make project state easier to observe before adding more automation.

Completed feature slices:

1. **Repo cockpit snapshot baseline**
   - Added `agent-remote cockpit snapshot --cwd <repo>`.
   - Shows the six operating lanes in one read-only repo snapshot.
   - Surfaces contradictions, `safe_to_mutate`, and a recommended next action.
   - Keeps cockpit read-only: no launch, cleanup, mutation, or implicit advance.

2. **Python 3.14 runtime support while keeping Python 3.13 compatibility**
   - Project support window is `Python >=3.13,<3.15`.
   - `.python-version` remains at the lower-bound dev target, `3.13.5`.
   - Stable Homebrew Python 3.14.4 was used for compatibility verification.
   - 3.14-only stdlib imports and syntax remain off-limits while 3.13 is supported.

3. **Cockpit Ralph→Team evidence slice**
   - Added `agent-remote cockpit snapshot --cwd <repo> --team-name <team>`.
   - Kept `--team <team>` as an alias.
   - Reads real Team status, tasks, events, and worker-status surfaces.
   - Promotes those reads into Ralph→Team lane `team_observations`.
   - Degrades read failures into warnings instead of mutating or aborting the whole snapshot.

4. **Development timeline tracking**
   - Added `docs/dev_timeline.md` to record this branch's cockpit work.

## Current merge-ready stopping point

The current branch should be merged after documenting this scope and preserving the tested cockpit baseline.

Merge-ready evidence from the current branch:

- `ruff` passed.
- `pyrefly` passed with `0 errors`.
- `pytest` passed with `651 passed`.
- Installed non-editable CLI smoke passed for:
  - `agent-remote cockpit --help`
  - `agent-remote cockpit snapshot --cwd . --team-name missing-team`

## Next feature direction after merge

The next work should be internal hardening, not broad automation.

Recommended near-term sequence:

1. **Typed transport hardening**
   - Clean `adapter_types` seams that still contain broad `object`, `dict[str, object]`, and unclear `str | None` contracts.
   - Start with `teamwork_types.py`, because it currently carries the most broad transport shape debt and is directly connected to cockpit Team evidence.
   - Use `typing_extensions.TypedDict` for PEP 728 features only at transport seams when useful.
   - Do not treat this as a broad Pydantic upgrade project.

2. **Cockpit team discovery slice**
   - Let cockpit discover linked Teams from persisted Goal/Ralph/Team state when `--team-name` is not provided.
   - Keep it read-only.
   - Do not invent filesystem mutation or implicit cleanup.

3. **Goal advance/watch prerequisites**
   - Add public `goal advance` / `goal watch` only after there is a truthful live repo/flow snapshot source and cockpit evidence is good enough to tell agents whether mutation is safe.
   - The existing `advance_tracked_codex_goal(...)` helper should not be exposed as a public mutating CLI until those prerequisites are met.

4. **Native OMX startup reliability hardening**
   - The adapter currently surfaces `ready_prompt_timeout` and startup issues as evidence.
   - Actual pane relaunch, same-assignment redispatch, and deeper startup repair belong in native OMX/runtime hardening, not cockpit mutation.

## Explicit non-goals for the next slice

- Do not make Python 3.14-only code the baseline.
- Do not replace Pydantic BaseModel artifact schemas with TypedDicts.
- Do not start a broad Pydantic dependency upgrade as a standalone feature.
- Do not add direct Goal→Team as a public lane.
- Do not make cockpit perform launch, cleanup, or implicit advance.
- Do not claim Hypergoal runtime support; Hypergoal remains planned/template-only.

## Current dependency decision

Keep the current dependency posture unless a concrete TypedDict hardening slice requires a tighter minimum:

- Keep Python support at `>=3.13,<3.15`.
- Keep Pydantic v2 as the primary schema/contract layer.
- If PEP 728 TypedDict features are adopted, use `typing_extensions.TypedDict`, not stdlib `typing.TypedDict`.
- If that adoption becomes part of production code, then tighten minimums deliberately, for example `pydantic>=2.12,<3.0` and `typing-extensions>=4.15,<5.0`.
