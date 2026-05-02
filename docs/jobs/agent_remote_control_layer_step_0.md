# Agent Remote Control Layer Master Plan

> For Hermes: execute serially, keep strict TDD, and treat UI as permanently out of scope for this repository.

**Goal:** Finish the OMX-first core adapter as a library-first runtime control surface with explicit transport, routing, promotion, interaction, runtime-state, and anomaly contracts.

**Architecture:** The adapter remains OMX-first but not OMX-only. Raw OMX output stays at the transport seam, normalization stays explicit, and stable contracts are emitted only after routing and promotion. Execution and runtime are treated as separate but parallel contract lanes, with anomaly/report semantics layered on top instead of mixed into transport parsing.

**Tech Stack:** Python 3.13.5, `uv`, Pydantic v2, `orjson`, Ruff, Pyrefly, pytest.

---

## Non-negotiable scope rules
- No UI
- No dashboard
- No frontend
- No presentation-first API design
- No premature generic runtime framework
- No speculative provider plugin architecture

## Repository paths that matter most
- `src/execution/payload_mapping.py`
- `src/execution/event_feed.py`
- `src/runtime/runtime_snapshot.py`
- `src/schemas/execution_schemas.py`
- `src/schemas/runtime_schemas.py`
- `src/schemas/common_schemas.py`
- `src/shared/exceptions/`
- `tests/execution/test_payload_mapping.py`
- `tests/execution/test_event_feed.py`
- `tests/runtime/test_runtime_snapshot.py`
- `docs/rules/`
- `.omx/context/`
- `.omx/plans/`

## Completion definition
This plan is complete only when:
1. execution lane semantics are explicit enough for downstream agent control
2. runtime lane semantics are explicit enough for downstream agent inspection
3. anomaly/report semantics are typed and useful without raw-payload guessing
4. OMX-specific assumptions are documented cleanly enough to support a later second runtime
5. docs and OMX artifacts match real code truth

## Ordered execution sequence
1. `docs/agent_remote_control_layer_step_1.md`
2. `docs/agent_remote_control_layer_step_2.md`
3. `docs/agent_remote_control_layer_step_3.md`
4. `docs/agent_remote_control_layer_step_4.md`
5. `docs/agent_remote_control_layer_step_5.md`
6. `docs/agent_remote_control_layer_step_6.md`
7. `docs/agent_remote_control_layer_step_7.md`
8. `docs/agent_remote_control_layer_step_8.md`

## Checkpoint policy
After every step:
- run the targeted test file first
- run full `uv run pytest`
- run `uv run ruff check .`
- run `uv run pyrefly check src`
- update `.omx/context/` if code truth changed
- update the relevant `.omx/plans/` file if plan truth changed

## Why a master plan exists
The numbered step files describe the actual work. This master file exists so implementers do not lose the big picture or accidentally reintroduce UI, backend-server drift, or premature generic abstraction.
