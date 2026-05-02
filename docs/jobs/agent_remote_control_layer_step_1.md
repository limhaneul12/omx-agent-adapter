# Agent Remote Control Layer Step 1

> For Hermes: follow strict TDD and repo rules. UI is explicitly out of scope.

## Goal
Stabilize and finish the OMX-first core adapter surface around execution and runtime normalization without introducing any UI or web-facing layer.

## Why this step exists
The repo already proved the execution/runtime control-surface direction. This step formalizes the near-term completion target for the **core library layer** so work does not drift into premature generalization or presentation concerns.

## Scope
- execution promotion and interaction/report surface
- runtime status normalization and typed state
- repo rules and OMX artifact sync
- no UI, no frontend, no dashboard

## In scope outcomes
1. Execution contracts remain stable and explicitly typed.
2. Runtime status contracts remain typed and normalization-first.
3. Anomaly/reporting semantics become easier for agents to consume.
4. OMX-first implementation is solid enough to serve as the reference runtime pattern.

## Out of scope
- web UI
- CLI polishing for humans first
- generic provider abstraction before another real runtime is integrated
- backend server work unless demanded by a later coordination slice

## Current baseline
Already present:
- `ExecMessage`, `ExecOutput`, `ExecToolCall`, `ExecToolResult`
- `ToolInteraction`, `ToolInteractionReport`, `ToolInteractionAnomaly`
- `RuntimeStatus` with active/mode status extraction
- anomaly buckets for unmatched/duplicate/missing-result states
- typed anomaly list

## Deliverables for this step
- a frozen short-term roadmap for the core library
- a step-by-step sequence that can be implemented serially
- docs that explicitly keep UI out of scope

## Verification
- plan files exist under `docs/`
- naming follows `{plan}_step_{number}.md`
- roadmap is library-first and UI-free
- steps are implementation-oriented, not product-marketing prose
