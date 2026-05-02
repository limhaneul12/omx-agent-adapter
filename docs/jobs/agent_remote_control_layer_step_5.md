# Agent Remote Control Layer Step 5

> For Hermes: follow strict TDD and repo rules. UI is explicitly out of scope.

## Goal
Prepare the OMX-first implementation to be a clean reference pattern for later non-OMX runtime integration.

## Why this is later
Do not jump here before execution/runtime OMX slices feel stable. Generic abstraction too early will dilute the signal.

## Work in this step
### 5.1 Identify true OMX-specific seams
Document which current assumptions are genuinely OMX-specific.

Examples:
- event payload shapes
- status output conventions
- mode naming semantics

### 5.2 Identify stable cross-runtime concepts
Only promote concepts that have already proven stable.

Strong candidates so far:
- execution contract promotion
- tool-call/result interaction grouping
- runtime status normalization lane
- anomaly reporting as a separate layer from raw transport

### 5.3 Introduce runtime adapter boundaries only where justified
Potential future shape:
- OMX adapter remains first concrete implementation
- later runtime adapters conform to the same high-level contract expectations

Do **not** design speculative plugin systems yet.

### 5.4 Define second-runtime readiness checklist
Before integrating another runtime, require:
- OMX-first semantics documented
- tests proving current contracts clearly
- boundary docs up to date
- exception vocabulary stable enough to compare behaviors

## Acceptance criteria
- repository has a clear statement of what is OMX-specific vs runtime-generic
- no premature generic framework work
- next-runtime integration can follow an explicit checklist
- UI remains out of scope

## Verification
- docs clearly distinguish OMX-first and future generic layers
- `.omx/context` and plan docs reflect the same framing
