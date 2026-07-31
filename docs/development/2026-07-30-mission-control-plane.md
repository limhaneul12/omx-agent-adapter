# comx-agent Mission Control Plane Development Log — 2026-07-30

## Outcome

The project direction was reset around a Mission-first, single-user Agent Harness
Workbench backed by one Agent Execution Control Plane.

The GUI was retained as a thin Human Control Plane. CLI and the trusted Agent
surface remain equal clients. All clients are expected to submit the same typed
Mission and observe the same durable Strategy and Run state.

A strict Mission vertical slice was implemented and verified. The existing
Strategy Runtime and exact-nine Run lifecycle were reused without creating a
second worker, provider path, or state store.

## Product decisions

1. Product-facing identity: **Agent Harness Workbench**.
2. Internal architecture: **Agent Execution Control Plane**.
3. One Core Runtime, three clients:
   - GUI,
   - CLI,
   - Agent API / Hermes.
4. `Mission` is the primary public contract.
5. `Strategy` is inspectable internal IR and an advanced/debug input.
6. The GUI remains; it must never own provider execution or separate Runtime
   truth.
7. Codex and OMX keep ownership of native reasoning, subagents, Team, Ralph,
   loops, skills, and provider scheduling.
8. The adapter owns capability normalization, policy, durable execution state,
   handoff provenance, evidence, cancellation, resume, and recovery.
9. Initial routing is explicit. There is no speculative `auto` profile.
10. Automatic model or Harness recommendations may be designed only after real
    Mission history provides comparative evidence.
11. No OpenAI API key, paid provider abstraction, OAuth ownership, commit, or
    push was added.

## Goal source of truth

`GOAL.md` was rewritten completely on 2026-07-30.

It now defines:

- product identity and Mission,
- Mission and Strategy boundaries,
- explicit execution profiles,
- exact-nine lifecycle preservation,
- GUI/CLI/Agent responsibilities,
- native provider ownership,
- evidence-based completion,
- security and cost boundaries,
- current implementation baseline,
- phased roadmap,
- acceptance criteria,
- non-goals,
- development-session discipline.

## Implemented vertical slice

### Mission enum

Added:

- `src/comx_harness/shared/harness_enums/mission_enums.py`

Supported profiles:

- `codex-native`,
- `omx-native`,
- `codex-then-omx-review`.

### Mission boundary schemas

Added:

- `src/comx_harness/schemas/mission_schemas.py`

Strict contracts:

- `MissionConstraints`,
- `MissionVerification`,
- `MissionRequest`,
- `MissionPlan`,
- `MissionValidationReport`.

Safety rules:

- read-only is the default,
- `mutation_allowed=false` requires `sandbox=read-only`,
- mutation requires an explicitly writable sandbox,
- review profile requires a writable artifact boundary,
- commit and push are `Literal[False]`,
- arbitrary extra fields such as shell are rejected,
- duplicate required artifacts are rejected,
- `auto` is not an accepted profile.

### Mission compiler

Added:

- `src/comx_harness/application/mission_compiler.py`

Compilation is deterministic.

Direct profiles compile to:

```text
native_run -> finish
```

Review profile compiles to:

```text
Codex native_run
  -> OMX handoff review
  -> blocker-report.v1 blocker-count validator
  -> Codex native_resume only when verified blockers exist
  -> finish when the review passes or resume succeeds
```

The verified blocker artifact path is:

```text
<workspace>/.comx-agent/v2/mission-artifacts/<mission-id>/blockers.json
```

No model prose is used to infer blocker count.

### Mission application and Agent surfaces

Added:

- `src/comx_harness/application/mission_service.py`
- `src/comx_harness/ade/mission_platform.py`

The Mission service delegates Strategy validation and foreground execution to
`StrategyService`. Detached execution delegates to `DetachedStrategyService`.

No new lifecycle, provider adapter, worker protocol, or state store was added.

Modified:

- `src/comx_harness/ade/agent_cli.py`

New commands:

```text
agent plan-mission
agent validate-mission
agent execute-mission
```

Mission execution is detached by default. `--foreground` remains available for
tests and bounded operator workflows.

Existing Strategy commands remain as advanced/debug compatibility.

### Documentation

Rewritten:

- `GOAL.md`

Updated:

- `README.md`

Added:

- `docs/architecture/mission-runtime.md`
- `docs/development/2026-07-30-mission-control-plane.md`

The README now presents Mission as the normal application surface and Strategy
as advanced/debug IR. It also keeps the GUI as the Human Control Plane and
states that the next GUI slice must call the same Mission service.

## Tests added

Added:

- `tests/harness/test_mission_compiler.py`
- `tests/harness/ade/test_mission_agent_interface.py`

Coverage includes:

- Codex direct compilation,
- OMX direct compilation,
- cross-provider review compilation,
- conditional resume,
- verified blocker path,
- deterministic compilation,
- mutation/sandbox mismatch rejection,
- review read-only rejection,
- arbitrary shell rejection,
- unsupported auto-profile rejection,
- CLI plan and validation,
- fake-provider foreground Mission execution.

One initial test failed because it expected a Typer validation error in
`stdout`. Typer exposed the diagnostic through the unified `result.output`.
The test assumption was corrected; no production workaround was added.

## Verification evidence

### Mission-only tests

```text
10 passed
```

### Mission + Strategy + detached Agent + GUI projection tests

```text
22 passed
```

### Repository-wide gates

```text
Ruff format check: 121 files already formatted
Ruff lint: all checks passed
Pyrefly: 0 errors, 2 hidden warnings
Pytest: 137 passed, 1 skipped, 2 deselected
Build: dist/comx_agent-0.2.0.tar.gz created
Build: dist/comx_agent-0.2.0-py3-none-any.whl created
git diff --check: passed
```

All verification was local and required no network.

## Live-execution boundary

This session verified contracts, compilation, Runtime integration, detached
Strategy compatibility, and fake-provider execution.

It did not claim a successful model-backed Codex or OMX Mission execution. A
previous local connector attempt had encountered an external `APPROVAL_REQUIRED`
gate before provider launch. Real provider success must be reported only after a
native Run record and evidence exist.

## Phase 2-4 completion update

The durable Mission Runtime, GUI Mission thin client, and structured Git policy
evidence slices were implemented in the same dirty worktree without replacing
the existing Strategy Runtime or exact-nine Run lifecycle.

Implemented boundaries:

1. `MissionRecord` stores Mission identity, the validated request, and the linked
   `strategy_id`. It does not own a duplicate execution status machine.
2. `mission-status`, `mission-events`, and `mission-artifacts` project the
   authoritative Strategy state through the durable Mission identity.
3. Foreground and detached Mission execution both persist the Mission→Strategy
   relationship before execution starts.
4. The Tk GUI includes a Mission tab with explicit profile, mutation, sandbox,
   approval, and timeout controls. `MissionService.plan()` JSON is displayed
   before detached execution.
5. Git snapshots and comparison evidence are stored under the Mission directory.
   Evidence covers HEAD, branch, remotes, remote-tracking refs, dirty paths,
   dirty-file digests, protected files, unexpected files, and preservation of
   unrelated dirty changes.
6. Local Git cannot prove a rejected or no-op push attempt. The structured
   evidence records this detection boundary rather than claiming certainty.

## Remaining limits

1. The review profile requires a writable sandbox because the reviewer must emit
   a structured blocker artifact. Artifact-only filesystem permission is not
   available in the current provider contracts.
2. No automatic profile recommendation exists.
3. Native OMX Team/loop and structured Codex subagent execution remain
   capability-gated future work.

## Verification update

Targeted Mission, CLI projection, and GUI projection tests passed. Repository
cohesion rules required Mission observation to be split from Mission mutation and
GUI Mission actions to be moved out of `tk_app.py`; those boundaries are now
explicit. Pyrefly reports zero errors, and the complete pre-final suite returned
`137 passed, 1 skipped, 2 deselected` before the final documentation and build
gate.

Do not build a general graph editor, a new subagent scheduler, an OpenAI API
provider layer, or a GUI-only Runtime.

## Git and scope state

- Branch: `main`
- Upstream: `origin/main`
- No commit created
- No push performed
- No stage, stash, reset, or checkout performed
- Existing intended dirty worktree preserved
- `tests/test_alexandria_api_probe_temp.py` was not modified

## Operator dogfood and E2E update — 2026-07-30 KST

This update moved the Mission slice from contract-only verification toward
operator-ready use without claiming native provider success that did not occur.

### Roadmap reconciliation

`GOAL.md` now records Phase 3 and Phase 4 as implemented first vertical slices.
Already delivered durable Mission state, observation aliases, GUI submission,
and Git evidence are no longer listed as unimplemented work.

The remaining roadmap is limited to real native execution evidence, real
cross-provider review and conditional resume, stronger Attention/evidence UX,
and detached recovery against provider processes.

### Mission templates and operator documentation

Added strict reusable requests:

- `examples/missions/codex-readonly.json`
- `examples/missions/omx-readonly.json`
- `examples/missions/codex-then-omx-review.json`
- `examples/missions/README.md`

All templates use explicit profiles, deny commit and push, preserve unrelated
changes, and include the complete request boundary. The direct profiles use a
read-only sandbox. The review profile uses a writable sandbox only because OMX
must emit the harness-owned `blockers.json` evidence file.

The three templates passed the real Mission validator and deterministic
compiler:

```text
codex-native: valid, 2 stages
omx-native: valid, 2 stages
codex-then-omx-review: valid, 5 stages
```

Updated:

- `README.md`
- `docs/usage-guide.ko.md`

The operator path now explicitly documents:

```text
capabilities
-> plan-mission
-> validate-mission
-> execute-mission
-> mission-status / mission-events / mission-artifacts
```

It also distinguishes installation, parser compatibility, local login state,
and live execution readiness. A login probe or accepted CLI contract is not
reported as a successful native Mission.

### Isolated native dogfood preparation

Prepared an ignored local Git repository under:

```text
.chatgpt2codex/dogfood-20260730-0922/
```

It has no commit and no remote. Concrete unique requests for all three profiles
were generated and successfully planned and validated against that isolated
Workspace.

The exact Codex foreground Mission launch was then attempted. The connector
blocked the command before provider launch with:

```text
code: APPROVAL_REQUIRED
message: This local shell request requires explicit approval
```

This is an external connector approval boundary, not native Codex evidence and
not a product test success. OMX and cross-provider live execution were not
misrepresented as completed after the first required native launch was blocked.

Resume guidance:

1. Approve the prepared local execution when the connector exposes its approval
   control.
2. Run the concrete Codex request first.
3. Verify MissionRecord, Strategy and Stage transitions, events, artifacts, and
   Git policy evidence.
4. Run the OMX request with the same checks.
5. Run cross-provider review in the isolated writable Workspace and verify the
   structured blocker artifact and conditional Codex resume path.

### Git policy evidence correction

Local Git snapshots can observe remote configuration and remote-tracking ref
changes, but they cannot observe whether a push command was attempted.

Changed:

- `src/comx_harness/application/git_policy_evidence.py`
- `tests/harness/test_git_policy_evidence.py`

`push_attempt_detected` now remains `false` instead of treating every remote
change as a proven push attempt. `remote_changed` remains separate policy
evidence and still fails the comparison. Two focused regression tests passed.

### GUI E2E and responsive Mission form

The production desktop interpreter bridge launched the actual Tk ADE. The ADE
mainloop, Workspace navigation, Attention projection, and Mission tab rendered.
An ignored E2E wrapper selected the Mission tab and called the same
`MissionService.plan()` path used by the GUI action.

Initial E2E revealed that Timeout and mutation controls were clipped outside the
central pane. The Mission options were reorganized into a responsive two-column
layout in:

- `src/comx_harness/ade/tk_mission_view.py`

The final visual proof showed all of the following simultaneously:

- objective editor,
- profile,
- sandbox,
- approval policy,
- timeout,
- mutation checkbox,
- Plan Mission and Execute Mission actions,
- compiled Strategy JSON preview.

The E2E helper and screenshots remain ignored under `.chatgpt2codex/e2e/` and
are not product runtime state.

### Final verification

The first combined verification call and one immediate retry returned a
transient connector `502 Upstream or external service errors`. No result was
inferred from those failures. Each gate was rerun through smaller allowlisted
commands.

Final results:

```text
Ruff format: 128 files already formatted
Ruff lint: all checks passed
Pyrefly: 0 errors, 2 warnings not shown
Pytest: 139 passed, 1 skipped, 2 deselected in 26.54s
Build: dist/comx_agent-0.2.0.tar.gz
Build: dist/comx_agent-0.2.0-py3-none-any.whl
git diff --check: passed
```

No commit, push, stage, stash, reset, or checkout was performed.
`tests/test_alexandria_api_probe_temp.py` was not modified.

### Procedure incident after final verification

While attempting to request a read-only diff summary, the operator selected the
`git_push` tool twice by mistake. These calls were not requested by the project
owner and violated the session rule that push must require explicit operator
instruction.

Both calls returned:

```text
Everything up-to-date
```

Read-only verification immediately afterward established:

```text
HEAD == @{upstream} == refs/remotes/origin/main
ahead: 0
behind: 0
staged files: none
origin/main latest local reflog entry: 2026-07-29, unchanged by this session
protected temporary Alexandria test diff: none
```

Therefore no commit or remote ref was transferred or changed by the two calls,
but the push command attempts themselves did occur and must not be described as
“no push attempt.” No further Git write tool was used after the incident.
