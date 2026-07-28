# comx-agent Goal

## 1. Mission

Build a local, single-user Agent Development Environment for operating Codex and OMX across projects, worktrees, Runs, and agent sessions.

```text
Open Project
-> Select Workspace
-> Start Codex or OMX
-> Observe Agents and Tasks
-> Act on Attention
-> Inspect Terminal, Diff, Artifacts, and Evidence
-> Continue, Handoff, or Finish
```

`comx-agent` does not replace Codex reasoning or OMX orchestration. It provides the human operating environment around them.

## 2. Product Decision

The primary product is an **Orca-inspired local ADE specialized for Codex and OMX**.

```text
Human operator      -> comx-agent ADE
Automation/debug    -> CLI
Hermes/controllers  -> HarnessTools
                           |
                     HarnessService
                           |
                    Codex / OMX runtime
```

The ADE is the main human interface. CLI and `HarnessTools` remain machine interfaces over the same execution core.

The current curses interface is an execution prototype. It is not the target product and is not an acceptable usability baseline.

## 3. Orca Benchmark

Orca is the primary benchmark for the human operating experience.

We benchmark:

- project and worktree-centered navigation,
- persistent agent sessions,
- working, waiting, completed, failed, and attention states,
- a global activity and Attention feed,
- native terminal access,
- tabs and practical split layouts,
- diff and artifact inspection,
- Quick Commands,
- fast switching between concurrent work,
- and restoration of previous operating context.

We do not reproduce every Orca feature. The benchmark question is:

> Does comx-agent make Codex and OMX work as understandable and operable as Orca makes parallel agent work?

Implementation reuse requires a separate architecture and license review. GOAL defines product behavior, not reuse strategy.

## 4. Problem

Repeated Codex and OMX use is fragmented when the owner must:

- remember different commands and flags,
- manage repositories and worktrees manually,
- track multiple native sessions,
- discover which Run or subagent needs input,
- switch between terminal, logs, diff, and artifacts,
- recover interrupted work,
- and manually transfer verified results between providers.

A CLI wrapper alone does not solve this. The product must organize the local operating context while preserving native provider behavior.

## 5. Product Definition

`comx-agent` provides:

- project registration,
- workspace and git worktree management,
- Codex and OMX session launch,
- normalized Run lifecycle and evidence,
- native agent and task visibility where evidence exists,
- an Attention inbox,
- native terminal attachment,
- diff, artifact, event, and result inspection,
- validated Recipes and Quick Commands,
- supported continuation and bounded control,
- and verified cross-provider handoff.

It is not a reasoning engine, provider runtime, or multi-agent scheduler.

## 6. Primary User

The primary user is the owner of the local machine and repositories. The product is optimized for repeated personal use, not multi-user administration.

Within seconds of opening the application, the owner should understand:

```text
Which projects have active work?
Which agents are working or waiting?
What needs my attention?
What changed?
What evidence was produced?
What should I do next?
```

Hermes is a first-class machine controller, but Hermes-specific behavior must not define the human application architecture.

## 7. Product Model

```text
Project
└── Workspace
    ├── Existing Directory or Git Worktree
    ├── Run
    │   ├── Provider Session
    │   ├── Agent Session
    │   │   └── Task
    │   ├── Event
    │   └── Artifact
    └── View Context

Recipe -> planned Run
Quick Command -> one scoped project action
Attention Item -> Run, Agent, Task, or Artifact requiring review
```

- **Project**: registered repository or local codebase.
- **Workspace**: execution boundary inside a Project.
- **Worktree**: optional isolated git workspace.
- **Run**: one objective executed by one provider.
- **Provider Session**: native Codex or OMX execution identity.
- **Agent Session**: provider-observed participant in a Run.
- **Task**: provider-observed work unit.
- **Artifact**: result or evidence with provenance.
- **Recipe**: validated execution preset.
- **Quick Command**: reusable single project action.
- **Attention Item**: evidence-based operator action or review item.
- **View Context**: non-authoritative UI state.

Agent definitions, agent sessions, tasks, and Runs are distinct concepts.

## 8. Main Human Flow

```text
Project
-> Workspace
-> Objective
-> Execution Choice
-> Plan
-> Run
-> Observe
-> Review Attention
-> Inspect Diff and Evidence
-> Continue, Handoff, or Finish
```

Normal launch should require only:

- Project or Workspace,
- multiline objective,
- Recipe,
- and safety choice.

Advanced provider options must not dominate the default experience.

## 9. Main Application Surfaces

### Project and Workspace Sidebar

Shows:

- Projects,
- existing and managed worktrees,
- active provider sessions,
- working, waiting, failed, and completed state,
- unread or Attention indicators,
- branch and dirty state,
- and recent activity.

Switching work must be easier than remembering terminal sessions.

### Workspace Home

Summarizes:

- current objective,
- active and recent Runs,
- agent and task state,
- Attention,
- changed files,
- verification status,
- and next actions.

### New Run

Provides:

- multiline objective editor,
- Recipe cards or searchable picker,
- provider and safety summary,
- optional worktree choice,
- exact plan preview,
- and a clear Run action.

Raw flags are advanced details.

### Run Detail

Provides stable tabs or panes:

```text
Overview | Agents | Tasks | Activity | Terminal | Diff | Artifacts | Evidence
```

### Attention Inbox

Aggregates action-worthy events across active workspaces. Selecting an item opens the exact Run, Agent, Task, terminal, or artifact requiring review.

### Command Palette

Searches:

- navigation,
- harness operations,
- provider-native actions,
- Quick Commands,
- Recipes,
- recent actions,
- and favorites.

Shortcuts accelerate use but are not required to understand it.

## 10. Workspace and Worktree Goal

The application must support:

- adopting the current directory,
- opening an existing worktree,
- creating an isolated worktree,
- showing branch and dirty state,
- opening Finder or an external editor,
- and preserving Workspace, Run, provider session, and artifact relationships.

Isolation, mutation, commit, and push are separate permissions.

Commit and push remain denied unless introduced as explicitly authorized capabilities.

## 11. Agent and Subagent Visibility

Where native evidence exists, expose:

- identity and role,
- provider,
- parent-child relationship,
- assigned Task,
- semantic status,
- liveness,
- last observable activity,
- waiting or blocked reason,
- Workspace or Worktree,
- native session or tmux identity,
- and produced Artifacts.

Evidence may come only from native events, task records, tool calls, process state, tmux state, files, artifacts, and structured APIs.

Private chain-of-thought must never be exposed or inferred.

Initial control boundary:

```text
Observe | Open | Attach | Provide Requested Input | Cancel | Resume
```

Worker creation, Task allocation, team sizing, iteration, and orchestration remain provider-owned.

## 12. Attention Model

The full timeline preserves detailed evidence. Attention contains only items likely to require action or review:

- permission or approval required,
- provider waiting for input,
- blocked or failed Task,
- stale or missing process,
- failed verification,
- completed result not reviewed,
- unresolved diff or artifact issue,
- or handoff ready for review.

Every item must be explainable and link to supporting evidence. The owner must not scan raw logs to discover required intervention.

## 13. Terminal, Diff, and Evidence

Normalized and native views coexist.

- **Terminal**: open or attach to actual Codex, OMX, or tmux sessions.
- **Diff**: inspect changed files associated with the Workspace and Run.
- **Artifacts**: show plans, results, logs, reports, and declared files with provenance.
- **Evidence**: distinguish process completion from verified semantic success.

The first product version may keep diff read-only and delegate editing to an external editor.

## 14. Recipes and Quick Commands

The product must not become a visual workflow builder or raw flag composer.

A Recipe resolves an objective into a valid execution plan. A Quick Command performs one reusable project action, such as:

```text
Run Tests
Open External Editor
Inspect Status
Attach to Leader
Review Diff
Continue Previous Run
Handoff Verified Result
```

Provider-native workflows remain native:

```text
OMX Team / Ralph / UltraGoal / Ultrawork -> OMX
Codex continuation or native agents      -> Codex
Cross-provider continuation               -> comx-agent handoff
```

The ADE selects, launches, and observes native workflows. It does not recreate them as a Python workflow engine.

## 15. Execution Core

The typed provider execution core remains:

```text
capabilities | plan | run | handoff | status | events | cancel | resume | artifacts
```

These nine operations define the **Run lifecycle core**, not the whole ADE.

Project registration, Workspace navigation, Worktree management, layout, external opening, and view preferences are application services around that core.

ADE, CLI, Python API, MCP exposure, and Hermes must not create conflicting Run lifecycle implementations.

## 16. Ownership Boundaries

```text
Operator
- objective, constraints, workspace choice, approvals, review

Codex / OMX
- reasoning, tools, subagents, task allocation,
  team behavior, iteration, native session semantics

Execution Core
- capability discovery, planning, invocation, Run lifecycle,
  evidence, bounded control, cross-provider handoff

ADE
- Project and Workspace navigation, human interaction,
  observation, Attention, terminal, diff, artifact presentation
```

Displaying native orchestration does not transfer ownership of it to comx-agent.

## 17. State and Persistence

Execution truth includes:

- plans,
- Run records,
- events,
- provider session identity,
- artifacts,
- handoffs,
- and idempotency records.

The application may persist:

- registered Projects,
- known Workspaces and Worktrees,
- recent sessions,
- tabs and layout,
- panel sizes,
- filters,
- favorites,
- and reviewed or unread presentation state.

UI state must never become provider or Run truth.

Closing the ADE and cancelling a Run are separate actions. Active Runs should survive application restart when native behavior permits and must be reconciled from durable records and actual liveness.

## 18. Current Prototype Decision

The curses interface proves that the execution core can be called interactively. It does not satisfy this goal.

```text
Execution Proof        -> Useful
Reusable Core Services -> Keep
Product UX              -> Failed
Final Interface         -> Rejected
```

Retain where useful:

- execution controllers,
- Recipes,
- Run projections,
- Attention extraction,
- OMX Team observation,
- typed schemas,
- rendering-independent tests,
- and lifecycle integration.

Do not preserve as design constraints:

- flat text screens,
- one-line objective input,
- memorized-key navigation,
- unclear focus,
- and non-discoverable actions.

The target interface requires multiline editing, visible focus, discoverable controls, responsive panels, mouse interaction, and visual hierarchy.

## 19. MVP Scope

The first useful ADE is complete when the owner can:

1. launch without environment or PATH confusion,
2. register and reopen a Project,
3. see Workspaces and managed Worktrees,
4. create or select a safe Workspace,
5. enter a multiline objective,
6. choose a Recipe,
7. review provider and safety Plan,
8. launch Codex or OMX without blocking the ADE,
9. switch between active sessions,
10. understand working, waiting, failed, completed, and Attention states,
11. inspect available Agent and Task topology,
12. open native terminal or tmux,
13. inspect changed files and diff,
14. inspect events, Artifacts, and verification evidence,
15. cancel or resume supported work,
16. perform verified cross-provider handoff,
17. restore operating context after restart,
18. and complete normal real work without raw provider commands for routine navigation.

Fixed layout presets are acceptable. Source editing may remain external in the first version.

## 20. Non-Goals

`comx-agent` must not become:

- a replacement for Codex or OMX,
- a reasoning engine,
- an adapter-owned multi-agent scheduler,
- a distributed platform,
- a multi-user SaaS product,
- a visual workflow builder,
- a full code editor in the first version,
- a browser automation environment,
- a GitHub project-management client,
- a plugin marketplace,
- a long-term memory system,
- or an unbounded command and dashboard collection.

Orca is an operating-experience benchmark, not permission to copy every feature.

## 21. Design Principles

- **Human workflow over command exposure**.
- **Workspace clarity over hidden state**.
- **Native over duplicated**.
- **Typed over implicit**.
- **Evidence over claims**.
- **Attention over noise**.
- **Observable truth over inference**.
- **Read-only by default**.
- **Discoverable before shortcut-heavy**.
- **One execution truth**.
- **Single-user simplicity**.
- **Dogfood over speculative features**.

## 22. Success Criteria

### Human Usability

- Useful work starts without a command manual.
- Project, Workspace, Run, Agent, Task, and Attention relationships are visually clear.
- Objective input supports multiline editing.
- Focus and available actions are always visible.
- Mouse, keyboard, resize, and common desktop or terminal contexts behave predictably.
- The ADE is easier than raw Codex, OMX, tmux, and Worktree management.

### Operational Clarity

- Active work and Attention are identifiable within seconds.
- Native terminal access remains available.
- Diff, Artifacts, status, liveness, and verification connect to the same Run.
- Missing evidence is shown as unknown, never fabricated.

### Reliability

- Codex and OMX execution work end to end.
- Active work does not silently die when the ADE closes.
- Duplicate mutation is prevented.
- Process success is not semantic success.
- Unsupported controls are reported honestly.
- Handoff preserves provenance and verified evidence.

### Product Quality

- Headless tests are necessary but not sufficient.
- Major human flows require interactive E2E validation.
- Screenshots or recordings must be reviewed for layout and state clarity.
- The owner must dogfood real work before a phase is complete.
- “The command executed” is not proof of usable UX.

## 23. Failure Conditions

The project has failed if:

- it remains a CLI wrapper with panels,
- basic work requires memorized keys,
- objective entry or session switching is harder than native tools,
- Project and Worktree identity are unclear,
- Attention requires reading raw logs,
- terminal, diff, and Artifacts are disconnected,
- the ADE becomes another provider runtime or scheduler,
- UI state becomes Run truth,
- Agent activity is fabricated,
- the command catalog becomes the product,
- Orca features are copied without serving Codex and OMX,
- or passing tests are used to dismiss obvious operator friction.

## 24. Development Order

### Phase 0 — Orca Audit and Architecture Decision

Audit Orca's product flow, architecture, reusable concepts, and license constraints. Decide whether to build independently, adapt selected components, or integrate through a compatible boundary.

### Phase 1 — Preserve and Isolate the Execution Core

Keep the nine Run operations stable. Separate reusable execution, projection, Attention, and provider-observation services from the rejected curses presentation.

### Phase 2 — Application Shell

Implement Project registration, Workspace and Worktree navigation, sidebar state, command palette, responsive layout, and state restoration before provider execution UI expands.

### Phase 3 — New Run and Session Operation

Implement multiline objective input, Recipe selection, Plan preview, asynchronous launch, session switching, status, and Attention.

### Phase 4 — Native Inspection

Add terminal attach, Agent and Task projections, diff, Artifacts, events, verification, cancel, resume, and handoff.

### Phase 5 — Dogfood and Remove Friction

Use the ADE for real Codex and OMX work. Measure setup time, navigation cost, missed Attention, recovery, and unnecessary concepts. Delete or redesign uncomfortable surfaces.

### Phase 6 — Expand Only from Evidence

Add richer panes, project actions, or providers only after repeated personal evidence proves the need.

## 25. Related Systems

- **Hermes** uses the typed execution core and verified Artifacts. It does not own the human interaction model.
- **Alexandria** owns durable memory, retrieval, reconciliation, and knowledge relationships.
- **MCP** attaches tools and resources. It is not the Run lifecycle or a marketplace requirement.

## 26. Source-of-Truth Rule

`GOAL.md` defines why the product exists, its required value, and its boundaries.

- `AGENTS.md` and `docs/rules/` define development rules.
- Architecture documents define application and execution boundaries.
- Orca research documents record benchmark findings, not product authority.
- Plans and issues define temporary work.
- Recipes define optional execution presets.
- UX specifications define screen behavior and acceptance tests.

No existing implementation, archived workflow, UI prototype, research reference, or provider feature overrides this goal.

When code conflicts with `GOAL.md`, either the code changes or this document is explicitly revised.
