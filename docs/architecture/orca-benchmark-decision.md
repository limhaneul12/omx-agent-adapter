# Orca Benchmark and Architecture Decision

## Decision

`comx-agent` will be built independently as a Codex/OMX-specific local Agent
Development Environment.

Orca is the operating-experience benchmark. Its source code and application
runtime are not imported in Phase 0.

This keeps one execution truth:

```text
ADE / CLI / HarnessTools
          |
   HarnessService
          |
     Codex / OMX
```

The ADE may project durable Run state, native provider evidence, and
non-authoritative view context. It may not replace the provider runtime or
create a second Run lifecycle.

## Upstream Snapshot

The review used `stablyai/orca` at commit
`54ed8c23110a65ba2bcc1e0154d750d3132ce834` on 2026-07-28.

The upstream material establishes these benchmark behaviors:

- isolated worktrees and centrally visible parallel agent sessions,
- persistent split terminals,
- diff inspection,
- Quick Open and fast switching,
- notification and unread state,
- host-owned terminal lifecycle and bounded restoration,
- and bounded structured search rather than indexing full terminal history.

References:

- [Orca README: product model](https://github.com/stablyai/orca/blob/54ed8c23110a65ba2bcc1e0154d750d3132ce834/README.md#L18-L21)
- [Orca README: worktrees, terminals, diff, Quick Open, and notifications](https://github.com/stablyai/orca/blob/54ed8c23110a65ba2bcc1e0154d750d3132ce834/README.md#L49-L67)
- [Orca terminal host authority](https://github.com/stablyai/orca/blob/54ed8c23110a65ba2bcc1e0154d750d3132ce834/docs/reference/remote-agent-session-host-authority.md#L80-L94)
- [Orca main-owned terminal restoration](https://github.com/stablyai/orca/blob/54ed8c23110a65ba2bcc1e0154d750d3132ce834/docs/terminal-main-owned-state.md#L18-L35)
- [Orca bounded session search](https://github.com/stablyai/orca/blob/54ed8c23110a65ba2bcc1e0154d750d3132ce834/docs/cmd-j-tab-session-search.md#L5-L24)

## Concepts Adopted

1. Navigate from Project to Workspace or Worktree before selecting a Run.
2. Keep live sessions and Attention visible without reading raw logs.
3. Treat terminal state as host-owned evidence and the UI as a replaceable
   projection.
4. Search only bounded structured metadata and revalidate a target before
   acting.
5. Persist view context separately from Run and provider truth.
6. Restore tabs and selection from view state, then reconcile them against
   durable records and actual liveness.
7. Show missing or stale evidence as unknown.

## Concepts Not Adopted

- a general runtime for arbitrary agent CLIs,
- adapter-owned orchestration, worker creation, or task allocation,
- Orca's PTY protocol as a replacement for Run identity or evidence,
- remote control, SSH, account switching, mobile, browser automation,
  GitHub/Linear management, or an embedded source editor,
- and unbounded terminal-history search.

## Architecture and Dependency Finding

Orca is an Electron application with main, daemon, preload, and React renderer
entry points. Its dependency graph includes Electron, React, Zustand,
`node-pty`, xterm, SSH, and native-module patching.

That stack does not provide a small reusable boundary for this repository's
Python `HarnessService`. Adapting it would add a second runtime, terminal owner,
and persistence model before the Codex/OMX-specific application shell is
proven.

References:

- [Electron entry-point configuration](https://github.com/stablyai/orca/blob/54ed8c23110a65ba2bcc1e0154d750d3132ce834/electron.vite.config.ts#L190-L208)
- [Orca runtime dependencies](https://github.com/stablyai/orca/blob/54ed8c23110a65ba2bcc1e0154d750d3132ce834/package.json#L182-L243)

## License Finding

Orca is MIT licensed, copyright Lovecast Inc. 2026. The license permits use and
modification when its copyright and permission notice are preserved in copies
or substantial portions.

No Orca source or asset is copied by this decision. A future reuse proposal
must identify a pinned upstream file and function-level need, preserve the MIT
notice, review transitive dependencies and assets, avoid trademark or
endorsement implications, and prove that the reused component does not create
conflicting execution truth.

Reference:

- [Orca MIT license](https://github.com/stablyai/orca/blob/54ed8c23110a65ba2bcc1e0154d750d3132ce834/LICENSE#L1-L20)

## Phase 0 Exit Criteria

- `HarnessService` remains the only Run lifecycle application core.
- Project, Workspace, Worktree, Run, Agent Session, Task, Artifact, Attention,
  and view context remain distinct.
- The rejected curses interaction model is not treated as the target UX.
- Application-shell work precedes additional provider or workflow features.
- Major human flows require interactive and visual evidence in addition to
  headless tests.
