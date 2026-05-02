# Agent Remote Control Layer Step 3

> For Hermes: follow strict TDD and repo rules. UI is explicitly out of scope.

## Goal
Deepen the runtime lane so runtime state becomes as agent-friendly as the execution lane.

## Target area
- `src/runtime/runtime_snapshot.py`
- `src/schemas/runtime_schemas.py`
- `tests/runtime/test_runtime_snapshot.py`

## Current baseline
Already present:
- `RuntimeStatus.summary`
- `has_active_modes`
- `active_mode_names`
- `mode_statuses`
- `unknown` bucket for unrecognized tokens

## Remaining work in this step
### 3.1 Per-mode object surface
Move from plain status maps toward mode objects if the extra structure clearly improves downstream use.

Possible direction:
- `RuntimeModeSnapshot`
  - `name`
  - `status`
  - optional flags later only if justified

### 3.2 Runtime anomaly/state visibility
Decide whether runtime status also needs explicit anomaly/state buckets analogous to execution report semantics.

Examples:
- stderr fallback used
- summary available but active state unresolved
- unknown status tokens observed

### 3.3 Runtime helper clarity
Keep parser helpers narrow and explicit.

Do not collapse:
- stdout parsing
- stderr fallback summary handling
- status typing

## Acceptance criteria
- runtime lane remains transport-aware and normalization-first
- any new structure improves agent consumption, not human display
- known/unknown semantics stay tested
- no UI-oriented presentation concerns leak into runtime modeling

## Verification
- `uv run pytest tests/runtime/test_runtime_snapshot.py -v`
- `uv run pytest`
- `uv run ruff check .`
- `uv run pyrefly check src`
