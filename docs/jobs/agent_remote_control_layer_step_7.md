# Agent Remote Control Layer Step 7

> For Hermes: follow strict TDD and repo rules. UI is explicitly out of scope.

## Goal
Lock down test and documentation quality so the OMX-first adapter surface can be trusted as the canonical reference implementation.

## Target area
- `tests/`
- `docs/rules/`
- `.omx/context/`
- `.omx/plans/`

## Work in this step
### 7.1 Test matrix review
Check whether the current tests leave obvious semantic gaps.

High-value candidates:
- repeated duplicate-result patterns
- larger mixed execution event sets
- runtime stderr fallback edge cases
- runtime unknown token combinations

### 7.2 Documentation truth sync
Make sure the plan files, `.omx/context`, and rules docs match what the code actually does now.

### 7.3 Execution/runtime capability summary
Add or update concise docs that explain what the adapter currently guarantees.

Good content:
- supported execution promoted shapes
- supported runtime normalization semantics
- anomaly/report semantics
- explicit statement that UI is not part of this repo’s goal

## Acceptance criteria
- tests reflect real semantics, not wishful design
- docs are aligned with code truth
- the current adapter surface can be understood without reading every source file

## Verification
- `uv run pytest`
- `uv run ruff check .`
- `uv run pyrefly check src`
- manual read-through of affected docs for truth alignment
