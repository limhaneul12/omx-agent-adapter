# ADE Architecture

## Decision

The first useful `comx-agent` ADE is an independently built native desktop
application using Python's standard-library Tk/ttk widgets.

This decision is intentionally narrow:

- the repository rule forbids adding a dependency without an explicit request,
- Tk is available in the supported local Python installation,
- native widgets provide multiline editing, visible focus, mouse interaction,
  resizable split panes, tabs, menus, dialogs, and a command palette,
- and the application stays in the existing Python wheel and process model.

The UI technology is replaceable. It owns no Run lifecycle truth.

The desktop launcher treats Tk availability as a runtime capability. On macOS,
it may bridge from a `uv` interpreter with missing Tcl resources to a compatible
Python 3.13 framework interpreter while preserving the invoking environment's
package paths. This boundary is tested and fails explicitly when no usable Tk
runtime exists.

## Boundary Diagram

```text
Tk application shell
├── Project / Workspace catalog and view context
├── Recipe, Run, Attention, Team, Diff, and Artifact projections
├── external Finder / editor / Terminal targets
└── detached operation launcher
             |
       HarnessTools
             |
      HarnessService
             |
       Codex / OMX
```

### Execution truth

Only the existing Workspace-local store owns Plans, Runs, events, provider
sessions, Artifacts, handoffs, and idempotency.

### Application truth

The global ADE store owns only registered Projects and Workspaces plus
non-authoritative view context. It is atomic JSON rather than a database because
the product is local and single-user and the state set is bounded.

### Provider truth

Codex and OMX retain reasoning, tools, subagents, Tasks, native sessions, and
orchestration. The ADE displays native Agent and Task evidence where it exists
and otherwise displays unknown.

## Process Survival

Long Run-like operations never use the Tk event thread.

The ADE writes one strict request under its state root and starts a packaged
worker with:

```text
python -m comx_harness.ade.worker
```

The worker starts in a new process session, redirects its own logs to durable
files, and calls exactly one `HarnessTools` operation. It is not a daemon or
scheduler. The ADE may exit immediately; the worker continues finalizing the
normal Workspace Run record and evidence.

Cancellation remains an explicit shared-core action.

## Terminal Decision

The first version does not embed a PTY or terminal emulator.

- Direct noninteractive Runs expose normalized events and stdout/stderr
  Artifacts.
- The ADE opens the selected Workspace in the real macOS Terminal.
- A tmux attach target is resolved only from an explicit observed identity.
- Missing terminal identity is unavailable, not guessed.

An embedded terminal would add a platform-specific process owner and is deferred
until dogfood proves external attachment inadequate.

## Diff and Artifact Decision

The Git inspection service is read-only. It reports current Workspace status,
staged and unstaged patches, untracked files, and rename provenance.

Unless a future Run baseline proves attribution, the UI labels the patch
“current Workspace diff; selected-Run attribution is unknown.”

Artifact content is read only after the selected path is revalidated against the
core `ArtifactReport`. Display is UTF-8-only and size-bounded. Binary, large,
missing, and read-error states remain explicit.

## Presentation Structure

The application uses a fixed three-pane shell:

```text
Projects / Workspaces | Workspace or Run tabs | Attention
```

The main area provides:

- Workspace Home,
- New Run,
- and Run Detail.

Run Detail provides:

```text
Overview | Agents | Tasks | Activity | Terminal | Diff | Artifacts | Evidence
```

Every routine action is available through visible buttons or menus. The
searchable command palette and keyboard accelerators are optional accelerators,
not required knowledge.

## Future Replacement Gate

Replacing Tk with Textual, Qt, Tauri, Electron, or another UI stack requires:

1. repeated dogfood evidence of a concrete usability or packaging failure,
2. explicit dependency approval,
3. proof that the replacement still uses the same application and execution
   services,
4. migration tests for Project/view state,
5. interactive and visual evidence,
6. and deletion of the superseded presentation rather than a compatibility
   facade.
