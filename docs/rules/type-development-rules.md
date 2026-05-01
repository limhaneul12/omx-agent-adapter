# Type Development Rules

## Goal

Keep production source code strongly typed, explicit, and predictable so that the adapter remains trustworthy as an agent-facing OMX control surface.

This repository is contract-heavy. Type discipline is therefore a design rule, not an optional cleanup concern.

## Core Direction

- Treat types as a first-class design concern.
- Missing or incorrect types in production source code are real defects.
- Prefer explicit contracts over loosely typed dictionaries or implicit conventions.
- Optimize for agent-facing runtime contracts, not backend-style domain modeling.

## Source of Truth Split

Detailed Pydantic-specific policy lives under:
- `docs/rules/pydantic/README.md`

Detailed boundary and transport-seam policy lives under:
- `docs/rules/schema-boundary-rules.md`

Use the Pydantic rule set for:
- schema design
- `ConfigDict` decisions
- `BaseModel` vs `RootModel` decisions
- strictness/default/nullability decisions
- contract modeling after routing/normalization
- enum/literal/shared-type decisions related to schema contracts

Use the boundary rule set for:
- transport parsing ownership
- JSON/JSONL seam policy
- routing/normalization ownership
- raw passthrough decisions

## Production Typing Rule

- Public adapter surfaces should be explicitly typed.
- Avoid pushing `dict[str, Any]` through the core adapter surface.
- Avoid broad `Any` unless the dynamic boundary truly requires it.
- If a runtime seam is inherently dynamic, localize that looseness to parsing/normalization boundaries and convert to explicit contracts quickly.

## Source vs Test Rule

- Production `src/` code should be held to a stricter standard than tests.
- Tests can be somewhat more flexible, but should not drive weak typing into production code.

## Pyrefly Rule

Pyrefly is the canonical static type checker for production source code in this repository.

Current direction:
- source code should stay type-clean under Pyrefly,
- production `src/` code should remain stricter than tests,
- do not silence type issues casually,
- do not use broad casts or `Any` as the first escape hatch.

## Design Principle

This repository should prefer one explicit, strongly typed contract language and a predictable static type discipline.

The detailed contract language rules are defined in the Pydantic rule set.
The broader repository typing policy is defined here.
