# Development Timeline

> Historical note: this file captures branch-level cockpit notes recorded before the per-day
> `dev_timeline/<YYYY-MM-DD>.md` routine existed. New dated progress entries should go under the
> repository-root `dev_timeline/` directory instead of extending this file.

## 2026-05-08 16:50 KST — Cockpit Ralph→Team evidence slice started

- Branch: `feat/agent-remote-cockpit`
- Baseline commits:
  - `c00764d feat: add repo cockpit snapshot surface`
  - `0f2608c feat: support python 3.14 runtime`
- Next slice: when `agent-remote cockpit snapshot` receives explicit Team names, read actual Team surfaces instead of only reporting placeholders.
- Target read-only evidence:
  - `omx team status <team> --json`
  - `omx team api list-tasks --input '{"team_name":"<team>"}' --json`
  - `omx team api read-events --input '{"team_name":"<team>"}' --json`
  - `omx team api read-worker-status --input '{"team_name":"<team>","worker":"<worker>"}' --json`
- Non-goals:
  - no Team launch
  - no cleanup
  - no Goal/Ralph mutation
  - no automatic worker fanout
- Live preflight evidence:
  - `command -v omx` → `/opt/homebrew/bin/omx`
  - `missing-team` status returns `status="missing"`
  - `missing-team` tasks/events/worker-status surfaces return structured JSON successfully

## 2026-05-08 17:04 KST — Cockpit Ralph→Team evidence slice implemented

- Added `--team-name` as an alias for the existing `--team` cockpit option.
- `agent-remote cockpit snapshot --team-name <team>` now reads and embeds:
  - Team status (`status`, `phase`, dead/non-reporting workers as worker candidates)
  - Team task count and task owners
  - Team event count and event workers
  - observed worker statuses for owners/event workers/dead/non-reporting workers
- Ralph→Team lane now promotes explicit Team evidence into `team_observations` and derives lane state from real Team status:
  - active/non-terminal statuses → `active`
  - all missing statuses → `missing`
  - otherwise → `unknown`
- Missing/partial read failures are surfaced as warnings instead of causing cockpit to mutate or abort the whole repo snapshot.
- Verification:
  - `uv run ruff check src tests` → pass
  - `uv run pyrefly check src` → `0 errors`
  - `uv run pytest -q` → `651 passed`
  - Python 3.14 targeted cockpit test with Homebrew `Python 3.14.4` → `5 passed`
  - installed non-editable CLI smoke: `agent-remote cockpit snapshot --cwd . --team-name missing-team`
- Live missing-team evidence:
  - lane `ralph_to_team` state: `missing`
  - team status: `missing`
  - task count: `0`
  - event count: `2`
  - worker statuses observed: `1`

## 2026-05-08 17:50 KST — Current feature development scope recorded

- Added `docs/current-feature-development-scope.md` as the merge-ready feature boundary for `feat/agent-remote-cockpit`.
- Recorded that the current branch stops at a read-only cockpit baseline, Python 3.13/3.14 support, explicit Team evidence reads, and timeline tracking.
- Recorded the next intended direction after merge:
  - typed transport hardening first, starting with Teamwork adapter types
  - then cockpit Team discovery without explicit `--team-name`
  - then Goal advance/watch only after truthful repo/flow snapshot prerequisites exist
  - native OMX startup reliability hardening outside cockpit mutation
- Recorded the dependency decision: do not start a broad Pydantic upgrade; use `typing_extensions.TypedDict` only when a concrete PEP 728 transport-hardening slice needs it.
