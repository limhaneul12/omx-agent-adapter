# Agent Strategy Runtime

## Purpose

The Strategy Runtime is a bounded application layer for caller-submitted execution plans. It lets a trusted Agent choose Codex, OMX, or a verified cross-provider sequence without turning `comx-agent` into a central reasoning system.

The Strategy Runtime is not a provider, provider API abstraction, general graph engine, shell executor, Team scheduler, or replacement for the exact-nine Run lifecycle.

## Ownership boundaries

The calling Agent owns:

- mission interpretation,
- Strategy selection,
- explicit rationale submitted with the request,
- provider and native-surface choice,
- completion criteria and failure policy.

The platform owns:

- capability discovery and compatibility validation,
- schema validation,
- safe local process execution,
- durable Strategy, Stage, Event, Artifact, and Evidence state,
- bounded sequence and conditions,
- reuse of Run, resume, handoff, status, and artifact operations,
- detached worker recovery and observation.

Codex and OMX continue to own native reasoning, native sessions, native Subagents, OMX Team scheduling, Ralph, UltraGoal, and other provider-native workflows. The platform records only structured native information that is actually observable.

The GUI is a read-only human control plane over Workspace Runtime state. It is not a Strategy state store.

## Capability model

`capability-matrix.v1` separates:

- `installed`: the native binary resolves locally,
- `authenticated`: live native authentication is known, unknown, or unavailable,
- `execution_ready`: the parser contract and live execution readiness,
- `unavailable`: the provider cannot currently satisfy native Run execution.

Each native capability is `supported`, `conditional`, `unsupported`, or `unknown`. A binary or accepted `--help` parser is not sufficient evidence of authentication.

The discovery boundary may execute a secret-safe local authentication status command. Codex uses `codex login status`; the platform records only the normalized state and a fixed explanation, never OAuth credentials or token material. OMX is marked conditionally authenticated when the local Codex login is present because its native execution delegates to Codex, but OMX execution readiness remains conditional until a live OMX Run succeeds.

Read-only native diagnostics such as `omx state list-active`, `omx state get-status`, and `omx capabilities lock/check` may prove that OMX state and capability surfaces are operational. They do not prove model-backed `omx exec`, Team execution, or native loop completion.

## Strategy schema

`strategy-definition.v1` supports:

- `native_run`,
- `native_resume`,
- `handoff`,
- `validator`,
- `finish`.

The first version is limited to one Workspace, at most 64 ordered Stages, previous-Stage dependencies, at most three attempts, and these conditions:

- all dependencies succeeded,
- any dependency succeeded,
- any dependency failed.

There is no raw command or arbitrary shell field. Native workflows that are discovered but not executable through the current typed native surface are rejected rather than emulated.

## Runtime reuse

A Strategy Stage delegates to `HarnessTools`:

- `native_run` -> `run`,
- `native_resume` -> `resume`,
- `handoff` -> `handoff`,
- validators -> `status` and `artifacts`,
- `finish` -> durable dependency state.

The Strategy worker owns only aggregate coordination. Provider process state remains in the existing Run records under `.comx-agent/v2/runs`.

## Evidence and conditional resume

A native Stage is successful only when required criteria are backed by normalized Run evidence, including exit status, semantic Run status, required artifact existence, non-zero size, and SHA-256 digest.

A blocker-driven branch uses a verified `blocker-report.v1` artifact:

```json
{
  "schema_version": "blocker-report.v1",
  "blocker_count": 2,
  "unresolved": ["integration test failure", "missing artifact"]
}
```

The validator confirms that the file is a verified artifact of the source Run before reading it. Model prose, logs, and chain-of-thought are not parsed to infer blockers. A caller can therefore express:

1. Codex native Run,
2. OMX handoff review producing `blockers.json`,
3. blocker validator with `continue` failure policy,
4. Codex native resume when any dependency failed,
5. finish when either the validator or resume succeeded.

## Durable state

Each Strategy is stored under:

```text
.comx-agent/v2/strategies/<strategy-id>/
```

The directory contains the submitted definition, launch envelope, aggregate record, ordered events, worker logs, and final result. Reusing a Strategy ID with a different definition is rejected.

The Agent interface exposes capability, validation, detached execution, launch status, Runtime status, events, and verified artifacts. The desktop GUI reads the same aggregate records and does not write execution truth.

## Current limitations

- Native workflow names such as Team, Ralph, and UltraGoal are discovered but not yet launched by `strategy-definition.v1`.
- Cross-Workspace Strategies are rejected.
- Interactive input is unsupported.
- Structured Codex Subagent topology remains unknown unless Codex exposes a native structured surface.
- Blocker branching requires an explicit verified JSON artifact.
- Strategy cancellation currently remains Run-level; aggregate cancellation is not a separate lifecycle operation.
- A successful local authentication probe does not promote `execution_ready` from conditional to supported; a live native Run and its verified evidence are still required.
