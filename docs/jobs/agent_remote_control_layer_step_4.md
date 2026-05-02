# Agent Remote Control Layer Step 4

> For Hermes: follow strict TDD and repo rules. UI is explicitly out of scope.

## Goal
Consolidate shared contract vocabulary and boundary discipline now that both execution and runtime lanes have meaningful typed surfaces.

## Target area
- `src/schemas/`
- `src/shared/`
- `docs/rules/`
- selected tests that prove boundary expectations

## Work in this step
### 4.1 Shared typed primitives review
Audit reusable aliases and keep only those that earn their reuse.

Candidates:
- non-empty string aliases
- literals that should remain local vs shared

### 4.2 Contract naming review
Ensure schemas still follow concept ownership and have not drifted into generic buckets.

Avoid:
- broad catch-all schema files
- helper naming that hides boundary meaning

### 4.3 Boundary rule sync
If current code truth teaches something new, update rule docs.

Likely docs:
- `docs/rules/schema-boundary-rules.md`
- `docs/rules/pydantic/03-boundary-normalization.md`
- `docs/rules/type-development-rules.md`

### 4.4 Exception vocabulary review
Check whether execution/runtime/domain exceptions need one more pass before a second runtime is integrated.

## Acceptance criteria
- shared types stay intentional and minimal
- schema naming remains feature-oriented
- docs match actual contract/boundary behavior
- no UI abstractions or presentation-specific types are introduced

## Verification
- docs updated only where code truth changed
- `uv run pytest`
- `uv run ruff check .`
- `uv run pyrefly check src`
