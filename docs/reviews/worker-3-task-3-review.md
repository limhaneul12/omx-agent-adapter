# Worker 3 Task 3 Review: verified transport/documentation findings

## Scope

This review records verified findings from worker-3's documentation-and-quality lane without editing shared runtime/team implementation files.

## Verified findings

### 1. `docs/future-runtime-readiness.md` is current in this worktree

The earlier drift suspicion did **not** reproduce in the current branch. The document already references the renamed `src/omx_remote/...` paths, including:

- `src/omx_remote/execution/event_feed.py`
- `src/omx_remote/execution/payload_transport.py`
- `src/omx_remote/execution/contract_promotion.py`
- `src/omx_remote/runtime/status/runtime_snapshot.py`
- `src/omx_remote/execution/invoke.py`
- `src/omx_remote/schemas/execution/event_schemas.py`
- `src/omx_remote/schemas/runtime/status_schemas.py`

### 2. Live `omx session search --json` returns extra transport-only fields

Verified on 2026-05-04 with:

- `omx session search hermes --json --limit 1`
- `omx session search hermes --json --limit 0`

Observed live result items include these fields beyond the public normalized snapshot:

- `transcript_path`
- `transcript_path_relative`

Current `src/omx_remote/history/session_search.py` intentionally strips those fields before validation, preserving the narrower public `SessionSearchSnapshot` contract.

### 3. Team API live task payloads include `description`, but the normalized read-only task snapshot does not

Verified on 2026-05-04 with:

- `omx team api list-tasks --input '{"team_name":"in-repo-documents-sky-c52d0521"}' --json`

Observed live task items include:

- `subject`
- `description`
- `status`
- `owner`
- `depends_on`
- `role`
- `delegation`
- `id`
- `version`
- `created_at`
- `claim`

Current normalized `TeamApiTaskSnapshot` exposes only:

- `id`
- `subject`
- `status`
- `owner`

This is a real transport-vs-public-contract gap, but it touches the shared teamwork surface and was not changed in this review lane.

### 4. One stale internal source path remains in a live-like teamwork fixture

`tests/teamwork/test_team_api_snapshot.py` still uses fixture text containing:

- `Own src/teamwork/team_snapshot.py`

The real module path in this repository is:

- `src/omx_remote/teamwork/team_snapshot.py`

This is low-risk cleanup, but it also sits in the teamwork lane and was left unchanged here to avoid overlap.

## Recommended low-risk follow-up order

1. **Teamwork fixture cleanup**
   - Refresh the stale fixture text in `tests/teamwork/test_team_api_snapshot.py` to the current module path.
2. **Decide whether `description` belongs in the public task snapshot**
   - If yes, add a failing test first using live-like `list-tasks` payloads, then widen `TeamApiTaskSnapshot` and its normalization path.
   - If no, document that `description` is intentionally transport-only.
3. **Keep history result transport fields transport-only unless product needs change**
   - Live evidence supports the current conservative normalization boundary.

## Files deliberately avoided

To stay file-ownership-safe in the current team lane, this task did not edit:

- `src/omx_remote/teamwork/*`
- `src/omx_remote/history/*`
- `tests/teamwork/*`
- `tests/history/*`
- `.omx/**`
- `docs/jobs/**`
