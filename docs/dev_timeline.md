# Development Timeline

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

## 2026-05-09 21:10 KST — Goal-scoped PRD generation/capture slice started

- Branch: `feat/goal-prd-generation-capture`
- Dogfood source: `test_project` Run 5 showed Goal mirror existed but `.omx/prd.json` did not, so Ralph correctly could not launch.
- Corrected boundary:
  - Goal prompt/objective drives a PRD-authoring pass.
  - The PRD-authoring pass emits typed `RalphPrdArtifact` JSON.
  - `agent-remote` validates/captures that JSON as `.omx/prd.json`.
  - Ralph consumes the validated PRD and drives execution/Team fanout.
- Scope recorded in `docs/jobs/goal-prd-generation-capture.md`.
- Non-goals: no automatic LLM invocation yet, no Team owner assignment fix in this PR, no product-code implementation.

## 2026-05-09 21:29 KST — Goal-scoped PRD generation/capture MVP implemented

- Added `agent-remote goal prepare-prd-prompt`:
  - reads the tracked Goal mirror
  - renders a Goal-scoped PRD authoring prompt
  - instructs the authoring agent to return only JSON matching `RalphPrdArtifact`
  - explicitly says not to act as Ralph, not to launch Ralph, and not to launch Team
- Kept `goal prepare-ralph` as a legacy alias path, but it now emits the corrected Goal-scoped PRD authoring prompt language.
- Added top-level `agent-remote prd validate`:
  - validates a generated PRD JSON file as `RalphPrdArtifact`
  - optionally captures it to `.omx/prd.json` for Ralph consumption
  - reports objective, fanout flag, worker count, and assignment worker IDs
- Improved Ralph missing-PRD preflight guidance:
  - Ralph consumes an approved PRD; it does not author one
  - next commands point to `goal prepare-prd-prompt` and `prd validate`
- Verification:
  - RED observed first: focused tests failed on missing `build_goal_prd_authoring_prompt`
  - `uv run pytest tests/runtime/test_codex_goal_supervisor.py tests/test_cli_entrypoint.py -q` → `79 passed`
  - `uv run pytest tests/runtime/test_codex_goal_supervisor.py tests/runtime/test_ralph_control.py tests/test_cli_entrypoint.py -q` → `100 passed`
  - `uv run ruff check src tests` → pass
  - `uv run pyrefly check src` → `0 errors`
  - `uv run pytest -q` → `735 passed`
  - `uv build --wheel` → built `dist/agent_remote-0.1.0-py3-none-any.whl`
  - installed wheel smoke: `agent-remote goal prepare-prd-prompt` and `agent-remote prd validate` both passed

## 2026-05-09 21:37 KST — PRD Team owner assignment slice started

- PR #11 was pushed and squash-merged into main as `9961b62 feat: add goal-scoped PRD capture surface (#11)`.
- Started branch `fix/prd-team-owner-assignment` from synced main.
- Scope recorded in `docs/jobs/prd-team-owner-assignment.md`.
- Dogfood target: PRD `team_worker_assignments` must survive as explicit Team DAG node `owner` values, not only as allocator `role` hints.

## 2026-05-09 21:44 KST — PRD Team owner assignment implemented

- Added RED regression for a 4-worker PRD Team plan:
  - expected `RalphTeamDagNodePayload.__required_keys__` to include `owner`
  - expected generated DAG nodes to preserve `owner=[worker-1, worker-2, worker-3, worker-4]`
  - RED output: missing `owner` required key and `KeyError: 'owner'`
- Implemented explicit `owner` in `RalphTeamDagNodePayload` and populated it from `TeamWorkerAssignment.worker_id`.
- Verification:
  - RED focused tests failed as expected before implementation
  - owner regression focused rerun → `2 passed`
  - `uv run pytest tests/runtime/test_ralph_control.py -q` → `22 passed`
  - `uv run ruff check src tests` → pass
  - `uv run pyrefly check src` → `0 errors`
  - `uv run pytest -q` → `736 passed`
  - CLI plan-only smoke generated a 4-node DAG with `owners=worker-1,worker-2,worker-3,worker-4`

## 2026-05-09 22:05 KST — Start adapter runtime structure refactor

- Branch: `refactor/adapter-type-runtime-structure` from synced main `9961b62`.
- Job doc: `docs/jobs/adapter-runtime-structure-refactor.md`.
- Scope:
  - move execution stable field keys and event normalizer registry into enum/type-contract surfaces,
  - move runtime status marker tables into adapter type contracts,
  - split cockpit snapshot aggregation by reader/builder/source/lane/decision/team/ultrawork responsibilities,
  - split Ultrawork state classification out of the control CLI/runtime module,
  - add explicit module/class cohesion development rules.
- Note: `fix/prd-team-owner-assignment` remains a separate local branch/commit and is not included in this refactor branch.

## 2026-05-09 22:08 KST — Adapter runtime structure refactor verified

- Split results:
  - `runtime/cockpit/` no longer keeps a thin `cockpit_snapshot.py` compatibility facade; callers import the direct concept modules under `snapshot/`, `sources/`, and `team_evidence/`.
  - `runtime/ultrawork/ultrawork_control.py` delegates state classification to `ultrawork_state_classifier.py`.
  - execution stable field keys and event payload normalizers now live under enum/type-contract modules.
  - runtime status marker constants now live under `adapter_types/type_contract/runtime_status_contract_type.py`.
  - `docs/rules/type-development-rules.md` now records module/class cohesion and adapter-type contract placement rules.
- `github_pr_status.py` rationale recorded: it is a dedicated read-only cockpit evidence source for branch PR/review/check operating decisions.
- Verification:
  - focused structure/runtime tests → `131 passed`
  - `uv run ruff check src tests` → pass
  - `uv run pyrefly check src` → `0 errors`
  - `uv run pytest -q` → `739 passed`
  - `uv build --wheel` → built `dist/agent_remote-0.1.0-py3-none-any.whl`
  - installed wheel smoke: `agent-remote version` and `agent-remote cockpit snapshot --help` passed
