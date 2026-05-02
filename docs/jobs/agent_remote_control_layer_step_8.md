# Agent Remote Control Layer Step 8

> For Hermes: follow strict TDD and repo rules. UI is explicitly out of scope.

## Goal
Prepare the repository for a future second runtime without building the second runtime yet.

## Why this is the final step
By this point the OMX-first implementation should be stable enough that generic lessons come from proven code, not imagination.

## Work in this step
### 8.1 OMX-specific vs generic mapping document
Write down what parts of the current code are:
- clearly OMX-specific
- clearly cross-runtime
- not yet decided

### 8.2 Future integration checklist
Create a checklist for adding runtime #2.

Checklist should require:
- no breakage to OMX contracts
- explicit mapping layer for runtime-specific payloads
- tests proving transport vs normalization vs contract behavior
- anomaly/report semantics mapped intentionally

### 8.3 Refusal list for premature genericization
Document what not to add yet.

Examples:
- provider registry system
- plugin marketplace thinking
- giant abstract base classes with no second implementation
- feature matrix DSLs

## Acceptance criteria
- second-runtime readiness is documented
- OMX-first contract truth is protected
- future generalization has guardrails
- no UI work appears in this phase either

## Verification
- docs exist and are concrete
- no speculative framework code added just to satisfy the docs
- `.omx/context` and `.omx/plans/` reflect the same future-facing stance
