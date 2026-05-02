# Future Runtime Readiness and Guardrails

## Purpose

This document captures the current OMX-first adapter seams that are already stable enough to reuse,
what remains OMX-specific today, and the guardrails for adding a second runtime later without
forcing speculative abstraction into the repository now.

UI, dashboard, and frontend concerns remain out of scope.

## Current Code Truth

### Clearly OMX-specific today

- `src/execution/event_feed.py`
  - Decodes OMX-flavored JSONL event streams line by line.
  - Understands `item.completed` wrapping and splits wrapped payloads before contract promotion.
- `src/execution/payload_mapping.py`
  - Promotes OMX execution payload shapes such as `message`, `output_text`, `tool_call`, and `tool_result`.
  - Treats raw payload dictionaries as a transport seam until routing selects a stable contract.
- `src/runtime/runtime_snapshot.py`
  - Reads `omx status` output and derives runtime state from OMX stdout/stderr conventions.
  - Assumes OMX mode lines use `name: status` formatting and that `No active modes.` is the idle summary.
- `src/execution/invoke.py`
  - Invokes OMX commands directly and is therefore bound to OMX command behavior.

### Clearly cross-runtime concepts already present

- `src/schemas/execution_schemas.py`
  - Stable execution contracts: `ExecMessage`, `ExecOutput`, `ExecToolCall`, `ExecToolResult`.
  - Interaction/report contracts: `ToolInteraction`, `ToolInteractionReport`, `ToolInteractionAnomaly`.
- `src/execution/payload_mapping.py`
  - The split between transport parsing, promotion, interaction grouping, and anomaly reporting.
  - Interaction state semantics (`completed`, `missing_result`) are downstream-control concepts, not OMX-only UI concerns.
- `src/schemas/runtime_schemas.py`
  - `RuntimeStatus` is already a normalized runtime-facing contract rather than a raw CLI dump.
- `docs/rules/schema-boundary-rules.md`
  - Boundary ownership, transport-seam discipline, and normalized public contract expectations.
- `docs/rules/type-development-rules.md`
  - Strongly typed production-source expectations that should hold for any future runtime adapter.

### Not yet decided / not yet proven generic

- Whether `ExecToolCall.arguments: str` should remain the only stable argument contract or gain a second normalized lane.
- Whether runtime mode state should stay as `mode_statuses: dict[str, RuntimeModeStatus]` or graduate to richer per-mode objects.
- Whether runtime normalization needs an anomaly/report surface comparable to execution reporting.
- Whether a second runtime will map cleanly onto the existing execution event kinds or require a transport-specific promotion fork.

## Second-Runtime Readiness Checklist

Before adding runtime #2, require all of the following:

1. **Protect existing OMX contracts**
   - Do not break `ExecMessage`, `ExecOutput`, `ExecToolCall`, `ExecToolResult`, `ToolInteraction`, `ToolInteractionReport`, or `RuntimeStatus` without an explicit contract migration.
2. **Keep a dedicated mapping seam**
   - New runtime payloads must stop at a runtime-specific transport layer before promotion into shared contracts.
   - Do not leak raw runtime-specific dictionaries into stable adapter outputs.
3. **Prove transport vs normalization vs contract boundaries in tests**
   - Add tests for transport parsing.
   - Add tests for runtime-specific promotion/mapping.
   - Add tests for final shared-contract behavior.
4. **Map anomaly/report semantics intentionally**
   - Decide how unmatched tool results, duplicate results, missing results, or runtime-state anomalies translate from the new runtime.
   - Do not silently drop mismatches just because the second runtime uses different transport words.
5. **Document OMX-specific assumptions before abstracting**
   - Capture which current rules depend on OMX event wrapping, status wording, or mode naming.
6. **Preserve repository rules**
   - Keep no-UI scope, explicit boundary ownership, Pydantic-first contracts, and strict type/lint/test gates.
7. **Add the second runtime only after real overlap is visible**
   - Shared abstractions must come from proven duplication, not anticipation.

## Refusal List: What Not to Add Yet

Do not add any of the following just to appear future-ready:

- provider registry systems
- plugin marketplace thinking
- giant abstract base classes without a second concrete implementation
- feature matrix DSLs
- cross-runtime capability negotiation frameworks
- presentation-first wrappers designed for dashboards or web UIs
- generic orchestration layers that hide the OMX transport seam before another runtime exists
- speculative normalized tool-argument parsing shared across runtimes without evidence from a second runtime

## Recommended Generalization Order

When runtime #2 becomes real, generalize in this order:

1. keep transport parsing runtime-local
2. compare promotion shapes against existing execution/runtime contracts
3. extract only the shared normalization/report pieces that both runtimes genuinely need
4. keep runtime-specific exceptions and mapping logic concept-owned until duplication proves otherwise

## Decision Rule

A concept should move from OMX-specific to cross-runtime only after both of these are true:

- the current OMX implementation already demonstrates stable value for agent-facing control, and
- a second runtime creates real duplication or a clearly shared contract need.

Until then, this repository should remain OMX-first, library-first, and explicit about where transport-specific behavior ends.
