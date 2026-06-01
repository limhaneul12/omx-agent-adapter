# Boundary and Normalization Rules

## Goal

Keep raw OMX payloads from spreading unchecked through the adapter.

## Boundary Categories

### 1. Agent input boundary
These are requests entering the adapter from callers.

### 2. OMX output boundary
These are payloads coming from OMX, including JSON, JSONL event lines, and normalized command outputs.

### 3. Adapter public output boundary
These are structured results returned to callers.

### 4. Settings/config boundary
These are validated settings inputs when configuration needs a schema.

## Early Normalization Rule

Raw OMX output should be converted into stable adapter contracts early, but not prematurely.

Preferred flow:
1. receive raw OMX output
2. parse the transport unit minimally
3. route or normalize based on event/source shape
4. validate the canonical contract boundary with Pydantic
5. pass structured values onward

Do not keep raw dictionaries moving through multiple layers when a stable schema can be defined.
Do not force every inbound payload into a canonical schema before transport parsing and routing are complete.

## Model Construction vs. Raw Validation Rule

Use Pydantic validation APIs for raw or untrusted boundary values, not as a
generic way to construct known internal payloads.

### Raw or untrusted inputs

Use `model_validate(...)` or `model_validate_json(...)` when the value came from
outside the trusted internal construction path.

Good candidates:
- CLI or MCP input payloads
- JSON files read from disk
- OMX JSON/JSONL output
- subprocess output
- runtime state loaded from artifacts
- caller-provided dictionaries

Preferred examples:

```python
request = CommandRequest.model_validate(raw_payload)
event = RuntimeEvent.model_validate_json(raw_event_bytes)
```

### Internal schema construction

When production code is assembling a schema from known internal values, prefer
the Pydantic constructor with explicit keyword arguments.

Preferred:

```python
state = CodexGoalLifecycleRestoredState(
    artifact_path=str(self.artifact_path_for_goal(goal_id)),
    bundle=bundle,
    next_resume_target=next_resume_target,
    ready_to_resume=True,
    summary=summary,
)
```

Avoid using `model_validate({...})` as a convenience wrapper around a dictionary
literal that was built in the same function from already-typed local values.
That pattern makes a trusted internal construction path look like a raw boundary
parse and encourages known payload dictionaries to spread.

### Dumping and writing

Do not make call sites choose ad-hoc dumping behavior every time a schema must
be written or returned.

Preferred direction:
- construct the schema with explicit keyword arguments,
- pass the schema object to a concept-owned writer or response builder,
- let that writer/builder call `model_dump(mode="json")` or
  `model_dump_json()` consistently.

This keeps call sites readable while preserving one clear serialization policy.

Example:

```python
write_schema_json(
    path=artifact_path,
    model=CodexGoalLifecycleRestoredState(
        artifact_path=str(self.artifact_path_for_goal(goal_id)),
        bundle=bundle,
        next_resume_target=next_resume_target,
        ready_to_resume=True,
        summary=summary,
    ),
)
```

If a JSON string is the final output, prefer `model_dump_json()` over
`model_dump(mode="json")` followed by a second JSON serialization step.
If a JSON-compatible Python mapping is required, use `model_dump(mode="json")`
at the writer/transport boundary.

## Schema Placement Rule

Keep schemas under `schemas/`.

Split them by concept using:
- `{concept}_schemas.py`

Examples:
- `execution_schemas.py`
- `runtime_schemas.py`
- `teamwork_schemas.py`
- `history_schemas.py`
- `bridge_schemas.py`

## Dynamic Boundary Rule

Some OMX surfaces may remain dynamic in practice.

When that happens:
- keep the dynamic handling localized,
- add a short justification comment if necessary,
- allow a raw passthrough lane when transport parsing succeeded but canonical schema promotion is not yet justified,
- convert to an explicit schema as soon as the stable structure is understood,
- do not let dynamic looseness leak into the stable adapter API.
