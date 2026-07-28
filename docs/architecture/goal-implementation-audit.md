# GOAL.md Implementation Audit

## Authority and Scope

`GOAL.md` is the product source of truth. This audit maps the current
implementation to the first useful ADE defined there. It does not narrow the
Goal to the older command-line harness.

The implementation keeps two explicit state categories:

```text
Execution truth                  Non-authoritative application state
------------------------------   -----------------------------------
Workspace .comx-agent/v2         ~/.comx-agent/ade
Plans and Run records            registered Projects and Workspaces
events and provider sessions     selected Project, Workspace, and Run
Artifacts and handoffs           active detail tab and window geometry
idempotency records              reviewed presentation state
```

## Phase 0 — Orca Audit and Architecture Decision

Status: implemented in
[`orca-benchmark-decision.md`](orca-benchmark-decision.md).

Decision:

- build independently,
- reuse Orca's workspace-first, Attention, terminal, bounded-search, and
  restoration concepts,
- import no Orca application code or assets,
- and keep `HarnessService` as the only Run lifecycle core.

The reviewed Orca snapshot is pinned. License and future-reuse gates are
recorded with upstream references.

## Phase 1 — Execution Core

The fixed Run lifecycle remains:

```text
capabilities | plan | run | handoff | status | events | cancel | resume | artifacts
```

`HarnessTools` and `HarnessService` expose the same exact nine operations. CLI,
ADE, detached workers, and Hermes-style controllers call those operations
instead of creating their own provider or lifecycle logic.

Core evidence includes:

- strict immutable request, plan, Run, event, Artifact, and handoff contracts,
- native Codex and OMX provider adapters,
- normalized provider JSONL/stdout/stderr,
- semantic evidence verification,
- atomic idempotency,
- bounded cancellation and supported native resume,
- process liveness independent from semantic status,
- and bidirectional verified cross-provider handoff.

### Exact plan correction

ADE requests receive an idempotency key before preview. A deterministic Run ID
is derived from that key, so the non-mutating preview and later detached
execution use the same Run directory, argv, and Artifact paths. This avoids the
prototype bug where a displayed plan and its executed Run had different
identities.

## Phase 2 — Application Shell

The application shell provides:

- a global typed Project and Workspace catalog,
- canonical-path deduplication and reopen timestamps,
- current-directory adoption,
- existing Git Worktree discovery from porcelain output,
- isolated managed Worktree creation under the application state root,
- real branch, dirty, missing, and non-Git state,
- a Project and Workspace sidebar,
- fixed responsive split panes,
- a searchable command palette,
- external Finder and editor actions,
- and atomic view-context restoration.

Managed Worktree creation performs only `git worktree add -b`. Commit and push
are not application capabilities.

## Phase 3 — New Run and Session Operation

The native desktop application provides:

- multiline objective editing,
- discoverable data-only Recipes,
- visible provider and safety summaries,
- exact typed Plan preview,
- an explicit preview-before-Run gate,
- detached Run, resume, and handoff workers,
- recent Run switching,
- semantic status and actual liveness,
- and a global Attention list linked back to Workspace and Run evidence.

Detached workers are per-operation processes, not a resident daemon or
scheduler. Each worker deserializes one strict request and calls one existing
`HarnessTools` operation. Closing the ADE does not signal the worker or native
provider process.

## Phase 4 — Native Inspection

Run Detail exposes stable panes:

```text
Overview | Agents | Tasks | Activity | Terminal | Diff | Artifacts | Evidence
```

The inspection boundary provides:

- normalized Run and provider events,
- verified Artifact metadata and bounded UTF-8 content,
- current Workspace staged, unstaged, untracked, and rename evidence,
- explicit notice when current diff attribution to the selected Run is unknown,
- read-only OMX Team Agent and Task projection from native JSON evidence,
- unknown Codex topology when no structured evidence exists,
- safe macOS Finder, editor, and Terminal argv without `shell=True`,
- explicit-only tmux target resolution,
- bounded cancel,
- supported resume,
- and verified cross-provider handoff.

Direct noninteractive `codex exec` and `omx exec` Runs expose stdout/stderr
Artifacts. The ADE does not fabricate an interactive terminal identity.

## MVP Acceptance Map

| # | Requirement | Current authoritative evidence |
| --- | --- | --- |
| 1 | launch without PATH confusion | packaged `comx-agent ade --cwd PATH`; tested Tk-capability bridge preserves the invoking package environment |
| 2 | register and reopen Project | typed catalog plus canonical-path persistence tests |
| 3 | see Workspaces and Worktrees | porcelain discovery, managed Worktree records, sidebar status |
| 4 | create/select safe Workspace | adoption constraints and `git worktree add -b` tests |
| 5 | multiline objective | native multiline text widget and interaction test |
| 6 | choose Recipe | discoverable Recipe list with provider/safety description |
| 7 | review Plan | strict JSON Plan preview and disabled Run action before preview |
| 8 | launch without blocking ADE | detached per-operation worker E2E |
| 9 | switch active sessions | Workspace Run table and selected Run restoration |
| 10 | lifecycle and Attention | semantic status, liveness, evidence-based global Attention |
| 11 | Agent and Task topology | native OMX Team projection; explicit unknown fallback |
| 12 | native terminal/tmux | external Terminal target and explicit tmux target policy |
| 13 | changed files and diff | read-only Git status/diff service and Run Detail pane |
| 14 | events, Artifacts, evidence | shared core reports plus bounded Artifact content |
| 15 | cancel and resume | shared core controls; resume unsupported without native session ID |
| 16 | verified handoff | shared cross-provider provenance and digest verification |
| 17 | restore context | atomic Project/Workspace/Run/tab/geometry/reviewed state |
| 18 | routine navigation without raw commands | menus, buttons, sidebar, tabs, and command palette |

## Truthfulness Boundaries

- A process exit code of zero is not semantic success.
- Required result, plan, and declared evidence must exist and be non-empty.
- Missing provider, Agent, Task, terminal, diff-attribution, or Artifact evidence
  is displayed as unknown or unavailable.
- UI review state does not change Run status or evidence.
- Agent activity is never inferred from model prose.
- Worker creation, Task allocation, and team orchestration remain provider-owned.
- Same-provider composition remains native; harness handoff is cross-provider.

## Verification Layers

Deterministic gates:

```bash
make ruff
make pyrefly
make test
make build
make ci
```

Native parser-contract checks are an explicit environment-dependent gate:

```bash
make native-test
```

The deterministic suite covers the nine-operation core, fake-provider
end-to-end behavior, idempotency, cancellation races, restart-safe detached
execution, Project/Workspace persistence, real temporary Git Worktrees, diff
inspection, external target resolution, Artifact content, and rendering-
independent ADE views.

Headless success does not prove product usability. Phase 5 additionally
requires:

- interactive keyboard, mouse, focus, resize, and multiline validation,
- reviewed application screenshots or recordings,
- restart while a provider Run is active,
- real Codex and OMX dogfood under available credentials and account state,
- tmux or native terminal attachment where structured identity exists,
- and recorded friction followed by deletion or redesign.

Any unavailable external validation remains a named gap; it is not replaced by
a green unit test.

Current Phase 5 evidence is recorded in
[`ade-dogfood-report.md`](ade-dogfood-report.md).
