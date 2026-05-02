# Agent Remote Control Layer Step 2

> For Hermes: follow strict TDD and repo rules. UI is explicitly out of scope.

## Goal
Finish the execution lane as a strong reference implementation of a runtime control surface.

## Target area
- `src/execution/payload_mapping.py`
- `src/schemas/execution_schemas.py`
- `tests/execution/test_payload_mapping.py`

## What is already done
- per-event promotion
- tool call/result pairing
- stream grouping
- report buckets
- typed anomaly list

## Remaining work in this execution-focused step
### 2.1 Interaction state semantics
Add an explicit interaction-level state so downstream code can branch on meaning without inferring from `result is None`.

Candidate examples:
- `completed`
- `missing_result`

### 2.2 Anomaly metadata enrichment
Extend `ToolInteractionAnomaly` only when real value is clear.

Good next candidates:
- short summary string
- optional source lane hint if needed later

Do **not** add speculative fields that are not used.

### 2.3 Raw-vs-normalized tool arguments policy
Decide whether `ExecToolCall.arguments: str` remains the stable contract or whether a second normalized lane is needed.

Important:
- preserve transport seam clarity
- do not force premature JSON parsing into the stable contract if runtime payloads are heterogeneous

### 2.4 Report/helper cleanup
Refactor helper internals only if tests stay green and semantics stay identical.

Examples:
- reduce repeated scans across event lists
- make anomaly assembly helpers smaller and clearer

## Acceptance criteria
- interaction state is explicit or intentionally deferred with documented reason
- anomaly objects are rich enough for downstream routing without bucket re-join for common cases
- argument handling policy is documented and reflected in tests
- execution helpers stay typed and readable

## Verification
- `uv run pytest tests/execution/test_payload_mapping.py -v`
- `uv run pytest`
- `uv run ruff check .`
- `uv run pyrefly check src`
