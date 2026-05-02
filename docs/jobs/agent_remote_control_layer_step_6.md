# Agent Remote Control Layer Step 6

> For Hermes: follow strict TDD and repo rules. UI is explicitly out of scope.

## Goal
Convert the current structured execution/runtime surfaces into a cleaner policy-ready core by tightening semantics rather than adding breadth.

## Target area
- `src/schemas/execution_schemas.py`
- `src/schemas/runtime_schemas.py`
- `src/execution/payload_mapping.py`
- `src/runtime/runtime_snapshot.py`
- matching execution/runtime tests

## Work in this step
### 6.1 Interaction state decision
Decide whether `ToolInteraction` should gain an explicit state field.

Candidate values:
- `completed`
- `missing_result`

Only add this if it simplifies downstream use enough to justify a contract change.

### 6.2 Runtime state parity review
Compare execution anomaly/state semantics with runtime state semantics.

Question:
- does runtime need a report/anomaly surface of its own, or is the current `RuntimeStatus` enough?

### 6.3 Contract simplification pass
Remove or reshape anything that now looks redundant after anomaly buckets and normalized anomaly objects exist.

Important:
- preserve meaning
- prefer simpler surfaces over clever ones

## Acceptance criteria
- interaction/runtime state semantics are intentional rather than accidental
- the core surface is easier to consume than before
- no UI or presentation-layer abstractions are added

## Verification
- focused execution/runtime tests as needed
- `uv run pytest`
- `uv run ruff check .`
- `uv run pyrefly check src`
