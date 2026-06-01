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
- Avoid broad `dict[str, object]` in production source unless the dynamic boundary truly requires it.
- If a raw dictionary shape must remain, keep it localized to the parsing/normalization seam and add a short justification comment explaining why a stronger contract is not yet justified.
- Avoid broad `Any` unless the dynamic boundary truly requires it.
- If a runtime seam is inherently dynamic, localize that looseness to parsing/normalization boundaries and convert to explicit contracts quickly.
- Do not use `cast(JsonObject, {...})` to bless a known payload shape. Create a Pydantic schema, `TypedDict`, or `msgspec.Struct` for the known shape and convert it at the transport boundary.
- Use `JsonObject` only when the payload is genuinely dynamic or already at a raw JSON transport seam. If fields are known, model them.
- Do not use `Model.model_validate({...})` merely to wrap a dictionary literal built from known internal values in the same function. Use the Pydantic constructor with explicit keyword arguments for trusted internal schema construction, then let a writer/response builder perform `model_dump(mode="json")` or `model_dump_json()` at the serialization boundary.
- Reserve `model_validate(...)` and `model_validate_json(...)` for raw or untrusted boundary values such as CLI/MCP input, JSON files, OMX output, subprocess output, runtime state loaded from artifacts, or caller-provided dictionaries.
- If a JSON payload uses keys that Python class syntax cannot express (for example `from`), prefer a `msgspec.Struct` with field aliases over functional `TypedDict(...)` declarations.
- For `TypedDict` payloads, prefer constructing through the `TypedDict` class (`Payload(key=value)`) or a named builder over annotating a raw dict literal (`payload: Payload = {...}`), unless incremental optional-key mutation makes the literal clearer.
- Command argument bundles should be immutable `tuple[str, ...]` by default. Use `list[str]` only when a command is intentionally built through mutation or required by an external API.
- For calls with multiple same-typed or easily-swapped arguments, prefer keyword arguments (`name=value`) over positional arguments. Positional arguments are acceptable for short, standard-library-style calls where readability is better.
- Avoid `@property` unless it represents a stable derived attribute that meaningfully improves the contract. Do not use properties to hide ordinary helper calls or avoid explicit method names.

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

## Return Style Rule

- Production source should prefer returning named local variables over direct expression returns.
- Especially in validation, normalization, transformation, and aggregation code, assign the final value to a clearly named variable before returning it.
- Use the variable name to make the returned meaning obvious to a future reader or agent.
- Trivial passthroughs may be tolerated, but named returns are the default preference.

## Import Placement Rule

- Production imports belong at module top level by default.
- Do not use local/lazy imports as an ordinary dependency-management pattern.
- If a local import appears necessary, first split the dependency boundary so
  the circular reference or heavy import path no longer exists.
- Keep a local import only when it is truly unavoidable at an external/runtime
  boundary, and document the reason next to that import.
- Do not introduce circular dependencies and then justify them with lazy
  imports; circularity is a design smell to remove.

## Comprehension Rule

- Prefer comprehensions for pure collection construction and straightforward
  transformations when they improve readability.
- Do not use comprehensions for side effects such as file writes, subprocess
  calls, logging, mutation-heavy assembly, or multi-step validation.
- Keep explicit loops when naming intermediate values, error handling, or
  ordered side effects make the code easier to audit.

## Async Boundary Rule

- Keep core transformation and schema logic synchronous by default.
- Introduce `async` only at real boundary points where the code waits on external I/O, subprocess execution, or stream ingestion.
- Prefer a thin async entrypoint over spreading `async` through pure helpers.
- When bridging existing blocking code, prefer `asyncio.to_thread(...)` at the boundary instead of rewriting pure internals into coroutine-style code.
- If the repository already depends on `asyncer`, prefer the existing typed
  `execution/async_boundary.py` wrapper around `asyncer.asyncify(...)` for
  async-to-blocking bridges instead of open-coding thread-pool calls at each
  call site.
- Use `asyncer.create_task_group(...)` only for real concurrent async I/O whose
  results are awaited as a group. Do not add task groups around sequential
  validation, schema construction, prompt rendering, or deterministic file
  transforms.
- Do not convert small deterministic helpers to `async` unless they actually await something meaningful.
- If a function becomes async, add or update tests so the async contract is explicit.

Examples of good async candidates in this repo:
- OMX subprocess/status invocation boundaries
- execution event-stream ingestion boundaries

Examples that should usually remain sync:
- payload normalization
- schema promotion
- anomaly assembly
- small parsing helpers with no external wait state

## Module and Class Cohesion Rule

- Runtime files should be split by concept/responsibility before they become omnibus control surfaces.
- A runtime module that grows past roughly 430 lines should be treated as a refactor trigger unless it is generated code or a deliberately documented transport table.
- Do not keep thin compatibility facades for unused internal modules. Move callers to the concept-owned module path in the same slice and delete the wrapper so cleanup is not done twice.
- Move source reads, builders, classifiers, decisions, and summaries into concept-specific modules or subfolders when a folder becomes crowded.
- Classes should group one cohesive behavior and normally expose no more than 6 methods. Split token normalization, snapshot classification, builders, and orchestration into separate classes/modules instead of making one manager class absorb everything.
- Stable field-name sets, runtime marker tables, enum-like string markers, and dispatch registries belong in `adapter_types/type_contract/` or shared enum classes, not inline in runtime/control modules.
- Do not create re-export bucket packages or marker-only `__init__.py` files to hide large modules; split the actual implementation files.

## Design Principle

This repository should prefer one explicit, strongly typed contract language and a predictable static type discipline.

The detailed contract language rules are defined in the Pydantic rule set.
The broader repository typing policy is defined here.
