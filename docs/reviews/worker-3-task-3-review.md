# Worker 3 Task 3 Review: runtime-readiness documentation drift

## Scope

This review captures verified documentation drift and adjacent low-risk maintenance findings without editing shared hot files directly.

## Verified documentation drift

The current `docs/future-runtime-readiness.md` document references pre-rename source paths, while the repository code now lives under `src/omx_remote/...`.

### Verified stale path mappings

| Document reference | Verified current path |
| --- | --- |
| `src/execution/event_feed.py` | `src/omx_remote/execution/event_feed.py` |
| `src/execution/payload_mapping.py` | `src/omx_remote/execution/payload_mapping.py` |
| `src/runtime/runtime_snapshot.py` | `src/omx_remote/runtime/runtime_snapshot.py` |
| `src/execution/invoke.py` | `src/omx_remote/execution/invoke.py` |
| `src/schemas/execution_schemas.py` | `src/omx_remote/schemas/execution_schemas.py` |
| `src/schemas/runtime_schemas.py` | `src/omx_remote/schemas/runtime_schemas.py` |

### Source evidence

- `docs/future-runtime-readiness.md:15`
- `docs/future-runtime-readiness.md:18`
- `docs/future-runtime-readiness.md:21`
- `docs/future-runtime-readiness.md:25`
- `docs/future-runtime-readiness.md:30`
- `docs/future-runtime-readiness.md:33`
- `docs/future-runtime-readiness.md:36`

## Adjacent review findings

### 1. Version drift risk

The package version is duplicated across multiple places:

- `pyproject.toml:3`
- `src/omx_remote/cli.py:29`
- `tests/test_cli_entrypoint.py:29`

This is not a documentation-only fix, but it is a clear maintenance risk because future releases can drift between package metadata, CLI output, and test expectations.

### 2. Stale internal path in fixture text

`tests/teamwork/test_team_api_snapshot.py:92` includes fixture text referring to `src/teamwork/team_snapshot.py`, while the real module path is `src/omx_remote/teamwork/team_snapshot.py`.

This looks like stale internal documentation embedded in test data.

### 3. Repeated stdout-to-contract normalization pattern

The following modules appear to repeat a similar flow of executing OMX commands, parsing stdout, and normalizing the result into validated models:

- `src/omx_remote/bridge/adapter_probe.py`
- `src/omx_remote/bridge/adapter_status.py`
- `src/omx_remote/bridge/adapter_envelope.py`
- `src/omx_remote/runtime/active_runtime_modes.py`
- `src/omx_remote/runtime/runtime_mode_status.py`
- `src/omx_remote/history/session_search.py`
- `src/omx_remote/teamwork/team_snapshot.py`

This is a code-quality observation only. It may justify a future refactor if behavior changes need to stay consistent across adapters.

## Recommended low-risk follow-up

If the leader wants a direct docs correction later, the safest targeted change is to update the stale paths in `docs/future-runtime-readiness.md` only, with no behavior changes.

## Files deliberately avoided

To stay file-ownership-safe in the current team lane, this task did not directly edit:

- `README.md`
- `docs/future-runtime-readiness.md`
- `docs/rules/*.md`
- `src/**`
- `tests/**`
- `.omx/**`
