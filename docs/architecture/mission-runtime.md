# Mission Runtime

## Purpose

The Mission Runtime is the primary public application contract for `comx-agent`.
It lets a human or a trusted higher-level Agent submit the same objective,
constraints, execution profile, and verification requirements without manually
authoring Strategy stages.

The product boundary is:

```text
GUI / CLI / Agent API
        |
      Mission
        |
 Mission Compiler
        |
  Strategy IR
        |
 Strategy Runtime
        |
 exact-nine Run lifecycle
        |
 Codex / OMX native execution
```

Mission does not create another provider lifecycle. It compiles into the existing
bounded Strategy Runtime, which delegates every provider operation to the
existing exact-nine Run lifecycle.

## One Core Runtime, three clients

The same application services must serve:

- the desktop GUI used by the local operator,
- the CLI used by either the operator or scripts,
- the typed Agent surface used by Hermes or another trusted controller.

No client owns separate provider launch logic, status inference, or durable state.
The Workspace `.comx-agent/v2` store remains the execution Source of Truth.

## Mission contract

`MissionRequest` is a strict Pydantic boundary containing:

- `mission_id`,
- `controller_id`,
- `objective`,
- `workspace`,
- explicit `execution_profile`,
- mutation and preservation constraints,
- verification requirements,
- timeout,
- normalized `RunOptions`.

Extra fields are forbidden. Mission has no arbitrary shell or Python execution
field.

The initial contract denies commit and push. Read-only is the default. Mutation
requires both:

- `constraints.mutation_allowed=true`, and
- an explicit writable sandbox such as `workspace-write`.

A writable sandbox without mutation permission, or mutation permission with a
read-only sandbox, is rejected before Strategy compilation.

## Explicit execution profiles

The first vertical slice supports exactly:

- `codex-native`,
- `omx-native`,
- `codex-then-omx-review`.

There is no `auto` profile.

This avoids embedding an unsupported opinion about which current model or
Harness is best. Automatic recommendations belong after real Mission history can
compare completion, verification, elapsed time, retries, regressions, valid
review blockers, and human intervention.

## Deterministic compilation

`MissionCompiler` is deterministic: the same validated Mission produces the
same `MissionPlan` and `StrategyDefinition`.

### Direct profiles

`codex-native` and `omx-native` compile to:

```text
native_run
  -> finish
```

The native Run receives the Mission objective plus normalized preservation,
commit, push, and evidence instructions. Provider selection remains explicit.

### Codex then OMX review

`codex-then-omx-review` compiles to:

```text
codex-primary
  -> omx-review handoff
  -> blocker-gate
  -> codex-resume only when blocker-gate fails
  -> finish when blocker-gate or resume succeeds
```

OMX must write one `blocker-report.v1` JSON artifact under:

```text
<workspace>/.comx-agent/v2/mission-artifacts/<mission-id>/blockers.json
```

The blocker validator accepts only an artifact already verified by the existing
Run lifecycle with existence, non-zero size, and SHA-256 digest. Provider prose
is not parsed as a substitute for blocker evidence.

The review profile currently requires a writable sandbox because the reviewer
must emit the structured blocker artifact. Its objective explicitly forbids
project-source mutation and restricts the intended write to review evidence.

## Relationship to Strategy

Strategy remains a first-class Runtime entity and an inspectable intermediate
representation.

It is retained as a public advanced/debug interface for:

- deterministic Runtime tests,
- expert callers,
- replay and diagnosis,
- future profile tooling.

Normal callers should submit Mission instead of constructing stages manually.

The Strategy node set remains bounded to:

- `native_run`,
- `native_resume`,
- `handoff`,
- `validator`,
- `finish`.

## Runtime reuse

Mission planning and validation use `MissionService`, which delegates Strategy
validation and execution to the existing `StrategyService`.

Detached Mission execution compiles and validates the Mission, then starts the
existing `DetachedStrategyService` worker. Mission does not introduce:

- another worker protocol,
- another state store,
- another Run identifier,
- another provider adapter,
- another cancellation or resume path.

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

## GUI role

The GUI remains the Human Control Plane.

The GUI observes durable Strategies and Stages and now submits a
`MissionRequest` through the same Mission service used by CLI and trusted
Agents. It renders the compiled plan before detached execution and continues to
read the durable Strategy and Run state.

The GUI must not gain:

- separate Mission compilation rules,
- provider-specific subprocess launch code,
- inferred success state,
- a GUI-only state store,
- a general arbitrary workflow editor.

A Mission form, explicit profile picker, readable plan preview, approval/failure
attention, and evidence review are sufficient for the current product scope.

## CLI surface

Primary Mission commands are:

```text
comx-agent agent plan-mission <mission.json>
comx-agent agent validate-mission <mission.json>
comx-agent agent execute-mission <mission.json> [--foreground]
comx-agent agent mission-status <workspace> <mission_id>
comx-agent agent mission-events <workspace> <mission_id>
comx-agent agent mission-artifacts <workspace> <mission_id>
```

Execution is detached by default. `--foreground` is intended for tests and
bounded operator workflows.

Existing Strategy commands remain available as advanced/debug compatibility.

## Durable Mission aggregate and Git evidence

`MissionRecord` stores the validated caller request and its compiled
`strategy_id`. It does not duplicate Strategy status, events, artifacts, or the
exact-nine Run lifecycle. Mission observation projects those authoritative
records through a Mission identifier.

```text
.comx-agent/v2/missions/<mission_id>/mission.json
.comx-agent/v2/missions/<mission_id>/git-before.json
.comx-agent/v2/missions/<mission_id>/git-policy-evidence.json
```

Git policy evidence compares read-only snapshots of HEAD, branch, remotes,
remote-tracking refs, dirty paths, statuses, and dirty-file SHA-256 digests. It
records commit, branch, remote, protected-file, unexpected-file, and unrelated
dirty-change preservation results as structured JSON. Local Git cannot prove a
rejected or no-op push attempt, so that limitation is stored explicitly rather
than inferred from model prose.

## Current limitations

1. The review profile needs a writable artifact boundary. Fine-grained
   artifact-only filesystem permissions are not available in the current native
   provider contracts.
2. Contract and fake-provider execution are verified. This document does not
   claim successful model-backed Codex or OMX execution unless a live run record
   exists.
3. Automatic profile selection is deliberately absent until evidence exists.

## Next vertical slice

The next highest-value implementation should be:

1. add a durable Mission record linked to the compiled Strategy,
2. expose Mission-level observation commands that reuse Strategy observation,
3. add the Mission form and plan preview to the GUI through `MissionService`,
4. add a post-run Git policy evidence gate for commit/push and unrelated-change
   boundaries,
5. dogfood direct and review profiles on real repository tasks and record
   comparable evidence before designing profile recommendations.
