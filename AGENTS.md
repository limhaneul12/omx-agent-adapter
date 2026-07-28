# omx-agent-adapter Development Conventions

## Source of Truth

Read these documents before non-trivial work:

1. `GOAL.md` — why the product exists, its boundaries, and its success criteria.
2. `AGENTS.md` — high-signal repository working rules.
3. The relevant documents under `docs/rules/` — detailed implementation policy.

Existing code never overrides `GOAL.md`. When implementation and goal conflict, change the implementation or explicitly revise the goal with a recorded decision.

## Product Positioning

This repository builds the thinnest useful controller-neutral execution harness for Codex and OMX.

It is:

- a typed contract for direct Codex and OMX execution,
- a normalized run lifecycle and evidence boundary,
- a verified cross-runtime handoff mechanism,
- and one shared application core for a human CLI, Hermes, or another trusted controller.

It is not:

- a new agent framework,
- a second reasoning engine,
- a fixed workflow catalog,
- a company or council simulator,
- a replacement for native Codex or OMX features,
- a memory system,
- an MCP marketplace,
- a distributed scheduler,
- or a GUI-owned lifecycle that bypasses the shared execution core.

## Public Surface

The core public operations are intentionally limited to:

1. `capabilities`
2. `plan`
3. `run`
4. `handoff`
5. `status`
6. `events`
7. `cancel`
8. `resume`
9. `artifacts`

A new public operation requires evidence that it owns a lifecycle, interoperability, evidence, or controller-contract problem that native Codex or OMX does not already solve.

## Native-First Rule

Codex owns Codex reasoning and native Codex workflows.

OMX owns Team, Ralph, UltraGoal, missions, capability locks, and other OMX-native orchestration.

The harness may discover and invoke native capabilities. It must not rebuild them as Python workflows. Same-provider composition should use the provider's native behavior by default. Harness composition is reserved for cross-runtime handoff or measurable isolation/evidence value.

## Architecture

The shipped package is `src/comx_harness/`.

- `schemas/` owns strict public Pydantic contracts.
- `native_provider/` owns native Codex and OMX invocation adapters.
- `storage/` owns the local single-user filesystem store.
- `event_normalization.py` owns JSONL/stdout/stderr normalization.
- `run_evidence.py` owns artifact verification.
- `native_execution.py` owns subprocess execution and process liveness.
- `application/harness_service.py` owns controller-neutral Run orchestration.
- `controller_surface.py` owns the exact-nine `HarnessTools` facade.
- `ade/` owns Project, Workspace, presentation, and detached-launch services.
- `cli.py` is a thin adapter over `HarnessTools`.

CLI, Hermes integration, MCP exposure, and future operator interfaces must call the same application service. No interface may own separate run truth.

## Boundary Ownership

Controllers own:

- objective interpretation,
- runtime selection,
- constraints,
- and whether another run is needed.

Native providers own:

- reasoning,
- tool selection,
- provider-specific workflows,
- and native session behavior.

The harness owns:

- validated invocation,
- run identity,
- state and liveness,
- event normalization,
- cancellation and supported resume,
- artifact provenance and verification,
- idempotency,
- and cross-runtime handoff.

Alexandria owns durable memory. MCP is an attachment mechanism. Neither belongs inside the harness lifecycle core.

## Type and Schema Rules

Detailed policy remains under `docs/rules/`.

High-signal rules:

- Public contracts use strict, immutable Pydantic models.
- Raw native JSONL remains localized to the event-normalization boundary.
- Do not spread `Any`, loose dictionaries, or transport payloads through core services.
- Required key presence and nullable values are distinct concerns.
- Production functions and public methods require explicit types.
- Use named, purpose-driven modules and identifiers.
- Keep provider-specific differences visible instead of creating false abstractions.

## Module Cohesion

- A production module approaching 430 lines is a refactor trigger.
- A class should own one cohesive behavior and normally expose no more than six public methods; application facades may expose the fixed nine-operation product surface when delegation remains thin.
- Split execution, evidence, event normalization, storage, and orchestration rather than creating a runtime manager omnibus.
- Do not add compatibility facades for unused historical code.

## Safety and Truthfulness

- Read-only execution is the default.
- Mutation requires explicit controller intent and a non-read-only sandbox.
- A process exit code of zero is not semantic success.
- Required evidence must exist and be non-empty before success is reported.
- Unsupported cancel or resume behavior must fail explicitly rather than be simulated.
- Same idempotency keys must not create uncontrolled duplicate mutation.
- Do not expose dangerous bypass shortcuts as product presets.

## Development Order

Follow the order in `GOAL.md`:

1. reduce duplicated and speculative surfaces,
2. stabilize direct Codex and OMX providers,
3. prove cross-runtime handoff,
4. connect Hermes through the shared core,
5. dogfood the ADE and expand operator interfaces only from demonstrated need.

## Verification

Use `uv` and run all gates before declaring completion:

```bash
make ruff
make pyrefly
make test
make ci
```

Also verify:

- `comx-agent --help` exposes only the intended public surface,
- capability discovery reflects the actual installed binaries,
- planning performs no workspace mutation,
- the wheel contains `comx_harness` and not removed legacy packages,
- direct execution and cross-runtime handoff are covered by local fake-provider end-to-end tests.

Do not commit or push unless the user explicitly asks.
