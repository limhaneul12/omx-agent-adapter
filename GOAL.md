# comx-agent Goal

Status: active
Last revised: 2026-07-30
Owner: single local operator

## 1. Product identity

`comx-agent` is a local, single-user **Agent Harness Workbench** backed by an
**Agent Execution Control Plane**.

It exists so that either a human or a trusted higher-level Agent such as Hermes
can use Codex and OMX through the same durable execution core.

The product is not a new coding model, not another chat application, and not a
replacement for Codex or OMX. It is the local operating layer that makes their
native execution capabilities safe to select, combine, observe, verify, resume,
and compare.

## 2. Mission

Build one local runtime where:

- a human can submit and control development work through a GUI or CLI,
- a trusted Agent can submit the same work through typed CLI or API contracts,
- Codex and OMX keep ownership of their native reasoning and orchestration,
- every execution has durable state, events, artifacts, and completion evidence,
- failures remain inspectable and resumable across process and session boundaries,
- no paid OpenAI API key or provider-owned OAuth implementation is required.

The operating principle is:

> One Core Runtime, three equal clients: GUI, CLI, and Agent API.

## 3. Product model

```text
Human                                      Trusted Agent / Hermes
  |                                                |
  | GUI or CLI                                     | typed CLI / API
  +-----------------------+------------------------+
                          |
                       Mission
              objective + constraints + verification
                          |
                    Mission Compiler
                          |
             inspectable bounded Strategy IR
                          |
                  Strategy Runtime
                          |
          exact-nine durable Run lifecycle
                 /                    \
        Codex native                OMX native
                 \                    /
                  events + artifacts
                          |
             Evidence and durable state
                          |
            GUI / CLI / Agent observation
```

No client owns a separate execution truth. GUI, CLI, and Agent API must call the
same application services and read the same durable records.

## 4. Primary public contract: Mission

The normal caller-facing contract is a typed `Mission`.

A Mission declares:

- a stable Mission identifier,
- the objective,
- the workspace,
- an explicit execution profile,
- mutation and preservation constraints,
- verification requirements,
- timeout and normalized Run options.

The caller should not need to manually author a multi-stage execution graph for
normal use.

Example conceptual request:

```json
{
  "schema_version": "mission-request.v1",
  "mission_id": "fix-tui-startup-001",
  "controller_id": "hermes",
  "objective": "Investigate and fix the TUI startup failure.",
  "workspace": "/project/omx-agent-adapter",
  "execution_profile": "codex-then-omx-review",
  "constraints": {
    "mutation_allowed": true,
    "preserve_unrelated_changes": true,
    "commit_allowed": false,
    "push_allowed": false
  },
  "verification": {
    "require_process_success": true,
    "require_semantic_success": true,
    "required_artifacts": []
  },
  "options": {
    "sandbox": "workspace-write",
    "approval_policy": "on-request",
    "search": false,
    "ephemeral": false
  }
}
```

## 5. Internal execution contract: Strategy

A `Strategy` is a bounded, inspectable intermediate representation compiled from
a Mission.

It is not the default human-facing product surface.

Strategy remains available for:

- advanced trusted callers,
- debugging,
- deterministic replay,
- Runtime tests,
- future expert tooling.

The first Strategy IR supports only:

- `native_run`,
- `native_resume`,
- `handoff`,
- `validator`,
- `finish`.

It must not accept arbitrary shell nodes, arbitrary Python execution, unbounded
graphs, or hidden provider routing.

## 6. Initial execution profiles

The first Mission contract supports exactly three explicit profiles:

1. `codex-native`
2. `omx-native`
3. `codex-then-omx-review`

The direct profiles compile to one provider-native Run followed by a finish gate.

The review profile compiles to:

```text
Codex native Run
  -> OMX verified handoff review
  -> blocker-report.v1 validator
  -> Codex resume only when verified blockers exist
  -> finish when review passes or resume succeeds
```

The review decision must be based on a verified structured artifact, not on
unstructured model prose.

There is deliberately no `auto` profile in the first slice.

Automatic model or Harness selection may be added only after the platform has
collected enough real evidence to compare:

- task type,
- selected model and Harness,
- completion rate,
- verification results,
- elapsed time,
- retries,
- human interventions,
- valid blockers discovered by review,
- regressions and false completion declarations.

Routing must become evidence-driven, not a hard-coded opinion about model names.

## 7. Native ownership boundary

Codex owns Codex-native behavior, including any native subagents, skills, session
semantics, and provider-specific execution behavior.

OMX owns OMX-native behavior, including Team, Ralph, loops, native workflows,
and provider-specific scheduling.

`comx-agent` owns:

- capability discovery,
- installation and authentication readiness normalization,
- Mission validation,
- Strategy compilation,
- policy and permission boundaries,
- durable execution state,
- process launch and observation,
- cancellation and resume routing,
- cross-provider handoff provenance,
- event normalization,
- artifact verification,
- evidence-based completion,
- recovery and operator attention.

The platform must not recreate provider-owned reasoning or subagent schedulers.

## 8. Exact-nine Run lifecycle

The existing Run lifecycle remains the stable lower-level execution contract and
must remain exactly:

1. `capabilities`
2. `plan`
3. `run`
4. `handoff`
5. `status`
6. `events`
7. `cancel`
8. `resume`
9. `artifacts`

Mission and Strategy are aggregate layers over this lifecycle. They do not
replace it and must not create a second provider execution path.

## 9. GUI direction

The GUI remains part of the product.

It is a thin **Human Control Plane**, not a separate IDE Runtime and not a second
source of truth.

The GUI should eventually let the operator:

- choose or register a Project and Workspace,
- enter a Mission in natural language,
- select an explicit execution profile,
- set mutation, sandbox, approval, and verification constraints,
- inspect the compiled Strategy in a human-readable form,
- start, pause where supported, cancel, and resume execution,
- observe current Stage, Provider, Run, events, artifacts, and evidence,
- see approval needs and failure reasons,
- review diffs and final evidence before accepting the result.

The GUI must call the same Mission service used by CLI and trusted Agents.

The GUI must not implement:

- its own provider launch logic,
- its own status inference,
- its own Mission or Strategy state store,
- hidden defaults that differ from CLI or Agent API,
- a full code editor or language server in the current scope,
- a visual arbitrary workflow builder.

The Strategy tree remains the authoritative execution observation surface. The
GUI Mission tab submits and previews Missions through the shared Mission service
without duplicating Runtime logic.

## 10. CLI and Agent API direction

CLI is a first-class product surface for both humans and Agents.

The primary Mission commands are:

```text
agent plan-mission
agent validate-mission
agent execute-mission
```

Strategy commands remain advanced/debug compatibility surfaces:

```text
agent validate-strategy
agent execute-strategy
agent strategy-launch
agent strategy-status
agent strategy-events
agent strategy-artifacts
```

The Agent API must be typed, deterministic, machine-readable, and safe for a
trusted local controller. Human-readable decoration must never corrupt JSON
contracts.

## 11. Why the product remains valuable as models improve

Model intelligence is not the durable moat of this project.

As models become stronger, the platform should remove unnecessary central
planning rather than compete with model reasoning.

The durable responsibilities are operational:

- what is installed and authenticated,
- which native capabilities are actually available,
- what permissions were granted,
- which workspace was changed,
- what process ran,
- what evidence proves completion,
- what artifacts were produced and digested,
- where execution failed,
- whether it can be cancelled or resumed,
- how one model or Harness performed relative to another,
- when a human must intervene.

A stronger model makes the Runtime more useful when the Runtime stays thin,
observable, and verifiable.

## 12. Durable state model

The Runtime must preserve enough state to reopen work after the original caller
or process exits.

Core entities are:

- Project,
- Workspace,
- Worktree,
- Mission,
- Mission Plan,
- Strategy,
- Stage,
- Run,
- Handoff,
- Event,
- Artifact,
- Evidence,
- Attention item,
- Execution profile.

The Source of Truth is durable local state under `.comx-agent`, not GUI widgets,
terminal scrollback, or transient in-memory objects.

## 13. Evidence-based completion

A Mission is not complete because a model says it is complete.

Completion must use normalized evidence such as:

- native process exit state,
- normalized Run status,
- required artifact existence,
- non-zero artifact size where applicable,
- SHA-256 digest,
- structured validator output,
- test, lint, typecheck, or build results when required,
- verified blocker count for review profiles.

Unstructured provider text may be displayed, but must not substitute for required
structured evidence.

## 14. Security and cost boundaries

This is a local personal tool.

The first product must:

- reuse already installed local Codex and OMX CLIs,
- reuse the operator's existing local login state,
- avoid requiring an OpenAI API key,
- avoid adding a paid provider abstraction merely to run the product,
- avoid owning OAuth tokens or implementing an authentication service,
- default to read-only execution,
- require explicit writable sandbox selection for mutation,
- reject arbitrary shell in Mission and Strategy contracts,
- preserve unrelated workspace changes,
- deny commit and push in the initial Mission contract,
- never claim live provider execution without actual evidence.

Single-user scope does not justify unsafe hidden behavior. It permits a smaller
product, not a less inspectable Runtime.

## 15. Current implemented baseline

The repository currently contains:

- the exact-nine typed Run lifecycle,
- Codex and OMX native adapters,
- durable Runs, events, artifacts, handoffs, cancellation, and resume routing,
- provider capability and authentication probes,
- Project, Workspace, Worktree, Recipe, Attention, CLI, and Tk GUI foundations,
- a bounded Strategy Runtime,
- detached Strategy execution and durable observation,
- read-only GUI Strategy projection,
- the Mission request contract,
- deterministic Mission-to-Strategy compilation,
- explicit initial execution profiles,
- Mission planning, validation, and execution CLI surfaces.
- durable Mission records linked to authoritative Strategy state,
- Mission status, event, and artifact projection commands,
- GUI Mission planning and detached submission,
- structured pre/post Git policy evidence.

This baseline must be reused rather than replaced.

## 16. Development roadmap

### Phase 1 — Runtime foundation

Status: implemented baseline.

- exact-nine lifecycle,
- provider-native planning and launch,
- durable state and events,
- artifact verification,
- resume, cancel, and handoff,
- fake-provider and lifecycle tests.

### Phase 2 — Strategy aggregate

Status: implemented first vertical slice.

- typed bounded Strategy IR,
- capability validation,
- sequential Stage execution,
- conditional resume,
- evidence gates,
- detached worker,
- Agent commands,
- GUI observation projection.

### Phase 3 — Mission public contract

Status: implemented first vertical slice.

- strict Mission schema,
- explicit execution profiles,
- deterministic Mission compiler,
- Mission plan and validation reports,
- Mission CLI and Agent surface,
- tests for safety boundaries and compilation,
- durable Mission records linked to authoritative Strategy state,
- Mission status, event, and artifact observation aliases,
- structured pre/post Git policy evidence.

Remaining:

- real native Codex and OMX execution evidence,
- real cross-provider review and conditional-resume evidence,
- native command-level commit and push-denial evidence beyond local Git
  snapshots.

### Phase 4 — Human Control Plane

Status: implemented first vertical slice.

- Mission form,
- execution profile picker,
- readable plan preview,
- detached Mission submission through the shared Mission service,
- existing live Stage and Run projection,
- operator dogfooding of the Mission form and compiled plan preview,
- responsive visibility of profile, sandbox, approval, timeout, and mutation
  controls,
- no GUI-specific Runtime state.

Remaining:

- stronger approval and failure Attention UX,
- Mission-oriented artifact and Git evidence review,
- reopen and detached-recovery verification against real provider processes.

### Phase 5 — Native capability expansion

Only after live contracts are verified:

- OMX Team and loop launch surfaces,
- provider-native structured subagent observation where genuinely available,
- richer Codex native session and resume evidence,
- detached recovery across real provider processes,
- explicit unsupported/conditional/unknown capability reporting.

### Phase 6 — Evidence-driven profile recommendation

Only after sufficient real Mission history exists:

- compare profiles by task class and evidence,
- expose recommendations with reasons and uncertainty,
- let Hermes or a human accept or override a recommendation,
- never silently route based only on a model version name.

## 17. Acceptance criteria

The product is successful when all of the following are true:

1. The same Mission JSON can be planned and validated by a human CLI or a trusted
   Agent without different semantics.
2. GUI, CLI, and Agent API call one Mission and Runtime service path.
3. A Mission compiles to an inspectable Strategy before execution.
4. Direct Codex and OMX profiles reuse the existing Run lifecycle.
5. Cross-provider review uses verified artifacts and conditional resume.
6. Runtime state can be reopened after the caller exits.
7. Unsupported or unknown native capabilities are reported rather than guessed.
8. Read-only is the default and mutation requires an explicit writable sandbox.
9. No API key, new paid provider, commit, or push is required to use the product.
10. Test, lint, typecheck, and build gates remain green.
11. Real provider behavior is distinguished from fake-provider and contract tests.
12. The GUI remains useful to the operator without becoming a second Runtime.

## 18. Explicit non-goals

The current product does not aim to become:

- a VS Code, Cursor, Codex app, or Orca clone,
- a full code editor,
- a multi-user SaaS,
- a cloud scheduler,
- an authentication or billing platform,
- a new foundation model,
- a replacement for provider-native subagents or teams,
- an arbitrary workflow graph engine,
- an autonomous router based on unsupported assumptions,
- an OpenAI API wrapper that creates new cost requirements.

## 19. Development discipline

Every implementation session must:

- freshly inspect repository state and rules,
- preserve unrelated dirty worktree changes,
- use typed boundary models,
- keep GUI, CLI, and Agent interfaces thin,
- reuse existing application services and lifecycle state,
- add the closest tests for each new contract,
- run Ruff, Pyrefly, tests, and build gates as applicable,
- report failures and live-execution limits honestly,
- leave a development journal with decisions, changed files, verification, known
  limits, and exact resume guidance,
- never commit or push unless the operator explicitly requests it.

## 20. Final product statement

`comx-agent` is a personal local workbench for operating Codex and OMX well.

A human uses GUI or CLI. Hermes or another trusted Agent uses typed CLI or API.
Both submit the same Mission, observe the same durable Runtime, and rely on the
same evidence.

The platform does not try to outthink increasingly capable models. It gives
those models a stable place to run, a clear permission boundary, durable memory
of what happened, and proof of whether the work actually succeeded.
