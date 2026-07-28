# omx-agent-adapter Development Conventions

## Source of Truth

Read before non-trivial work:

1. `GOAL.md` — product purpose, boundaries, success criteria, and development order.
2. `AGENTS.md` — high-signal repository working rules.
3. Relevant documents under `docs/rules/` — detailed implementation policy.

Existing code never overrides `GOAL.md`. When code and goal conflict, change the code or explicitly revise the goal with a recorded decision.

## Product Positioning

This repository builds an Orca-benchmarked, local, single-user Agent Development Environment specialized for Codex and OMX.

The ADE is supported by a thin controller-neutral execution core. It provides:

- Project, Workspace, and Git Worktree operation,
- human desktop navigation and Attention handling,
- a typed non-GUI ADE application surface for agents,
- direct Codex and OMX execution,
- normalized Run lifecycle and evidence,
- bounded control and verified cross-provider handoff.

It is not:

- a new reasoning engine or provider runtime,
- an adapter-owned multi-agent scheduler,
- a replacement for native Codex or OMX features,
- a workflow catalog or visual workflow builder,
- a memory system or MCP marketplace,
- a distributed or multi-user platform,
- or a GUI-owned lifecycle that bypasses the shared execution core.

## Two Public Boundaries

### Run lifecycle core

The provider lifecycle remains exactly:

1. `capabilities`
2. `plan`
3. `run`
4. `handoff`
5. `status`
6. `events`
7. `cancel`
8. `resume`
9. `artifacts`

A new lifecycle operation requires evidence that native Codex or OMX and the existing nine operations cannot solve the lifecycle, interoperability, evidence, or controller-contract problem.

### ADE application surface

Project, Workspace, Worktree, catalog, and cross-workspace Attention are application services around the Run core. They may be exposed through the desktop ADE, `AdeAgentTools`, and `comx-agent agent ...` without becoming new Run lifecycle operations.

Human capabilities with clear agent value must have a typed non-GUI path unless they are explicitly documented as human-only. Agents must not automate GUI widgets to reach an application service that already has a typed domain boundary.

## Native-First Rule

Codex owns Codex reasoning and native Codex workflows.

OMX owns Team, Ralph, UltraGoal, missions, capability locks, worker allocation, and other OMX-native orchestration.

The platform may discover, launch, observe, attach to, and safely control native capabilities. It must not rebuild them as Python workflows. Same-provider composition uses native behavior by default. Cross-provider continuation uses verified handoff.

## Architecture

The shipped package is `src/comx_harness/`.

- `schemas/` owns strict public Pydantic contracts.
- `native_provider/` owns native Codex and OMX adapters.
- `storage/` owns authoritative local Run storage.
- `application/harness_service.py` owns controller-neutral Run orchestration.
- `controller_surface.py` owns the exact-nine `HarnessTools` facade.
- `ade/` owns Project, Workspace, Worktree, Attention, presentation, and detached-launch services.
- `ade/agent_platform.py` owns the typed non-GUI ADE facade.
- `ade/agent_cli.py` owns JSON commands for trusted agents.
- `cli.py` is the thin top-level CLI composition root.

Desktop ADE, agent CLI, Python APIs, Hermes, and future MCP exposure must reuse these services. No interface may create separate Project, Workspace, or Run truth.

## Boundary Ownership

Operators and controllers own:

- objective interpretation,
- provider and Workspace selection,
- constraints and approvals,
- and whether another Run is needed.

Native providers own:

- reasoning,
- tools,
- native subagents and task allocation,
- provider workflows,
- and native session semantics.

The Run core owns:

- validated invocation,
- Run identity, state, and liveness,
- event normalization,
- cancellation and supported resume,
- artifact provenance and verification,
- idempotency,
- and cross-provider handoff.

The ADE application layer owns:

- Project registration,
- Workspace and Worktree discovery or creation,
- non-authoritative view state,
- cross-workspace observation and Attention projection,
- and human or agent navigation over existing truth.

Alexandria owns durable memory. MCP attaches tools and resources. Neither belongs inside Run lifecycle truth.

## Type and Schema Rules

Detailed policy remains under `docs/rules/`.

High-signal rules:

- Public contracts use strict, immutable Pydantic models.
- Internal DTOs use typed dataclasses where boundary validation is unnecessary.
- Raw native JSON remains localized to normalization boundaries.
- Do not spread `Any`, loose dictionaries, or transport payloads through services.
- Required key presence and nullable values are distinct concerns.
- Production functions and public methods require explicit types.
- Use named, concept-owned modules and identifiers.
- Keep provider differences and unknown evidence visible.

## Module Cohesion

- A production module approaching 430 lines is a refactor trigger.
- A class normally exposes no more than six public methods.
- `HarnessTools` and `HarnessService` may expose the fixed nine-operation lifecycle facade when delegation remains thin.
- Split execution, evidence, storage, application services, and presentation instead of creating manager omnibuses.
- Do not add compatibility facades for unused historical code.

## Safety and Truthfulness

- Read-only execution is the default.
- Mutation requires explicit controller intent and a non-read-only sandbox.
- Worktree creation does not authorize commit or push.
- A zero process exit code is not semantic success.
- Required evidence must exist and be non-empty before success is reported.
- Unsupported cancel, resume, topology, or provider state must be explicit.
- Same idempotency keys must not create uncontrolled duplicate mutation.
- Do not infer agent activity or private reasoning from model prose.
- Do not expose dangerous bypass shortcuts as product presets.

## Development Order

Follow `GOAL.md`:

1. preserve and isolate the typed execution core,
2. maintain one shared Project, Workspace, and Worktree service,
3. keep human and agent application surfaces in parity,
4. improve Codex/OMX native observation and operation without duplicating them,
5. verify real human and agent workflows,
6. dogfood and expand only from repeated evidence.

## Verification

Before completion run:

```bash
make ruff
make pyrefly
make test
make ci
```

Also verify:

- `comx-agent --help` exposes only intended surfaces,
- `comx-agent agent context` returns structured platform state,
- Project registration and Worktree creation use the same services as the GUI,
- planning performs no Workspace mutation,
- capability discovery reflects installed binaries,
- the wheel contains `comx_harness` and not removed legacy packages,
- direct execution, handoff, and agent application commands have tests,
- major GUI flows receive interactive E2E review when presentation changes.

Do not commit or push unless the user explicitly asks.
