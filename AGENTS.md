# omx-agent-adapter Development Conventions

This repository builds an agent-facing adapter layer that helps multiple agents use OMX consistently and safely.

## Project Positioning

- This project is **not** a new agent framework.
- This project is **not** MCP itself.
- This project is **not** a replacement for OMX.
- This project **is** a control surface / adapter layer that helps agents operate OMX as a stateful runtime.

## Rules Source of Truth

Detailed development policy should live under `docs/rules/`.

Use `AGENTS.md` for high-signal working rules and navigation.
Use `docs/rules/` for longer source-of-truth policy documents.

Before making non-trivial structural or implementation changes, read the relevant rule documents first.
At minimum, contributors should check the rule set that matches the work they are doing.

Current rule documents:
- `docs/rules/type-development-rules.md`
- `docs/rules/naming-rules.md`
- `docs/rules/schema-boundary-rules.md`
- `docs/rules/lint-and-typecheck-rules.md`
- `docs/rules/pydantic/README.md`

Recommended reading order for normal code work:
1. `docs/rules/type-development-rules.md`
2. `docs/rules/schema-boundary-rules.md`
3. `docs/rules/pydantic/README.md`
4. `docs/rules/naming-rules.md`
5. `docs/rules/lint-and-typecheck-rules.md`

Rule ownership summary for agents:
- `docs/rules/type-development-rules.md`
  - repository-wide typing discipline
  - `src/` vs `tests/` strictness expectations
  - broad `Any` / loose dict usage policy
- `docs/rules/pydantic/README.md`
  - index for all Pydantic-specific schema rules
  - use this when changing model shape, validation, defaults, strictness, or normalization
- `docs/rules/schema-boundary-rules.md`
  - repository-level boundary ownership and leakage rules
  - JSON/JSONL transport seam policy, routing/normalization expectations, and raw passthrough guidance
  - use this to decide where raw transport data must stop and which module owns normalization
- `docs/rules/naming-rules.md`
  - filename and module naming policy
  - use this before creating new files or splitting an existing concept
- `docs/rules/lint-and-typecheck-rules.md`
  - verification gates and lint/typecheck expectations
  - use this before final validation and when deciding whether a warning can be ignored

## Architecture Direction

- Prefer a **library-first** architecture.
- Keep the CLI **thin** and let reusable logic live in importable Python modules.
- Treat OMX as the runtime/substrate and this repository as the agent-facing remote control layer.
- Favor structured contracts and machine-readable outputs over ad-hoc text parsing wherever possible.

## Source Layout Conventions

- Manage source code directly under `src/` by **feature/domain**, not under a nested `src/omx_agent_adapter/` package directory.
- Prefer clear feature slices such as:
  - `execution/`
  - `runtime/`
  - `teamwork/`
  - `history/`
  - `bridge/`
  - `parsing/`
  - `shared/`
  - `schemas/`
- Do not introduce a redundant package-name repetition pattern when the repository name already carries the project identity.

## Naming Rules

- Prefer **purpose-driven filenames** over generic technical filenames.
- Avoid vague or overly broad filenames such as:
  - `enums.py`
  - `utils.py`
  - `types.py`
  - `helpers.py`
  - `status.py`
  - `stream.py`
- Prefer filenames that describe role and intent, for example:
  - `runtime_snapshot.py`
  - `event_feed.py`
  - `payload_mapping.py`
  - `command_blueprint.py`
- Avoid filenames that can collide with common library/module names or create ambiguity later.
  - Example anti-patterns: `pandas.py`, `enum.py`, `typing.py`

## Pydantic Usage

For detailed Pydantic policy, read:
- `docs/rules/pydantic/README.md`
- `docs/rules/type-development-rules.md`

Short version:
- use `schemas/` for Pydantic-based contracts,
- keep schemas concept-split with `{concept}_schemas.py`,
- treat Pydantic v2 as the primary schema/contract system for this repository,
- use `type-development-rules.md` for repository-wide typing policy and `docs/rules/pydantic/` for schema-specific rules,
- do not treat Pydantic as the default raw transport parser in runtime/event-stream paths when a transport seam still needs routing or normalization.

## Type Strictness Policy

For detailed type rules, read:
- `docs/rules/type-development-rules.md`

Short version:
- type discipline is a first-class goal,
- missing or wrong types in production source are real defects,
- `src/` should remain stricter than tests,
- keep dynamic looseness localized to parsing or runtime-boundary seams.

## Exception Organization

- Manage cross-cutting exceptions under `shared/exceptions/`.
- Group exception files by concept/domain using the pattern:
  - `{concept}_exceptions.py`
- Examples:
  - `execution_exceptions.py`
  - `runtime_exceptions.py`
  - `teamwork_exceptions.py`
  - `history_exceptions.py`
  - `bridge_exceptions.py`

## Shared Enums and Shared Types

- A `shared/` folder is allowed and encouraged when it holds genuinely cross-cutting definitions.
- Do **not** place all enums in a single `shared/enums.py` file.
- Keep enums with enums, but split them by concept.
- Recommended structure:

```text
shared/
└── omx_enums/
    ├── runtime_enums.py
    ├── execution_enums.py
    ├── teamwork_enums.py
    ├── history_enums.py
    └── bridge_enums.py
```

- Apply the same principle to other shared cross-cutting definitions: keep similar things together, but still split by concept instead of building giant catch-all files.

## Python Version and Tooling

- Use `uv` for environment and dependency management.
- If using Python 3.13, prefer the latest stable patch release in the 3.13 line that is officially available.
- At the time of writing, the currently recommended 3.13 patch release is `3.13.5`.
- Python version decisions should consider practical ecosystem compatibility, not only language-version preference.

## Implementation Guidance

- Start with the smallest viable adapter surface around proven OMX commands.
- Favor structured, testable wrappers around:
  - `omx exec --json`
  - `omx state ... --json`
  - `omx team ... --json`
  - `omx adapt ... --json`
- Prefer safe, read-only verification paths before adding mutating or interactive flows.
- Do not overbuild backend/server infrastructure early; justify it with actual coordination requirements.
- In runtime/event-stream code, keep the layer split explicit:
  - transport parsing (`orjson`)
  - routing/normalization
  - stable contract validation (`Pydantic`)
- If a payload may remain partially raw or heterogeneous, preserve that fact at the transport/normalization layer instead of forcing premature schema unification.

## Typed Transport Contract Rule

- In concept-owned transport or normalized `TypedDict` definitions, do not leave required-vs-optional key presence implicit.
- Use `Required[...]` for keys the seam contract truly guarantees.
- Use `NotRequired[...]` only for keys that may genuinely be absent at that seam.
- Do not force `Required[...]` onto raw nested payload shapes whose upstream variability is still intentional or not yet split into honest discriminated transport types.
- Required key presence and nullable value semantics are separate concerns. A key may be `Required[...]` even when its value is still normalized to `None` before schema validation.
- Top-level stable subset payloads should prefer explicit `Required[...]` / `NotRequired[...]` annotations because they make agent-facing contract intent obvious.

## General Principle

When in doubt:
1. keep the structure feature-oriented,
2. keep contracts explicit,
3. keep filenames purposeful,
4. keep shared definitions grouped by kind and split by concept,
5. keep the adapter easier for agents to use than the raw OMX surface.
