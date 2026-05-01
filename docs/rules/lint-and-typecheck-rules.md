# Lint and Typecheck Rules

## Goal

Keep quality gates explicit and repeatable so that the adapter remains reliable as a typed, contract-heavy OMX control layer.

This repository treats linting and static type checking as development rules, not optional cleanup work.

## Core Direction

- Ruff is the canonical formatter and linter.
- Pyrefly is the canonical static type checker for production source code.
- Production source code should stay green under both tools before work is considered complete.
- Tests may be somewhat more flexible than production source, but they should still remain readable and maintainable.

## Ruff Rule

### Role

Ruff is responsible for:
- formatting
- linting
- import ordering
- basic correctness checks
- keeping code style predictable

### Current direction

Ruff should be run against the repository and kept passing for normal development work.

The project currently favors a fairly strong lint surface while avoiding unnecessary rule noise.

### Expectations

- Prefer fixing code over suppressing warnings.
- Avoid broad `# noqa` usage.
- If suppression is unavoidable, keep it narrow and justify it.
- Do not casually loosen Ruff policy just to get temporary green output.

## Pyrefly Rule

### Role

Pyrefly is the canonical static type checker for production source code in this repository.

### Current direction

- Keep `src/` under strict type-check expectations.
- Treat missing or incorrect types in production source as real defects.
- Avoid broad `Any`, broad dictionaries, and casual casts.
- Localize runtime-driven looseness to parsing or boundary seams and convert it to explicit schemas quickly.

### Expectations

- Fix type errors before claiming completion.
- Do not bypass Pyrefly with lazy escape hatches unless there is a documented reason.
- Prefer improving schema clarity and explicit contracts over silencing checker complaints.

## Source vs Test Policy

- `src/` is the stricter target.
- `tests/` can be more pragmatic.
- Do not let test convenience dictate weak typing or weak structure in production code.

This means:
- production contract code should be lint-clean and type-clean,
- tests may tolerate more direct assertions or lightweight fixtures,
- but tests should still avoid becoming chaotic or misleading.

## Rule Change Policy

Changing lint/typecheck policy affects the entire repository.

Because of that:
- do not change Ruff or Pyrefly configuration casually,
- do not weaken rules just to avoid a local refactor,
- document any policy change clearly when it is truly necessary.

## Commands

Preferred verification commands:

```bash
uv run ruff check .
uv run pyrefly check src
uv run pytest
```

If formatting support is needed:

```bash
uv run ruff format .
```

## Completion Rule

Before considering a meaningful code change done, the normal expectation is:

1. Ruff passes.
2. Pyrefly passes for `src`.
3. Relevant tests pass.

If one of these is intentionally deferred, that decision should be explicit rather than silently ignored.

## Design Principle

This repository is building a control surface that other agents will trust.

That means lint and typecheck are not secondary polish.
They are part of the contract quality of the project itself.
