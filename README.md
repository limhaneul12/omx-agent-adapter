# agent-remote

Agent-facing control layer that helps agents use **OMX + Codex strongly** through typed, inspectable operating routes.

## What this repo is for

`agent-remote` is not just a thin wrapper around raw OMX commands. The project direction is to make agents better at operating the Codex/OMX stack by giving them route selection language, typed state, safe evidence collection, runtime guardrails, and lifecycle artifacts.

The intended top-level operating lanes are intentionally small and fixed:

| Lane | Status | Meaning |
| --- | --- | --- |
| Goal only | Implemented baseline | Native Codex Goal objective loop with adapter-tracked mirror state, status, and template surfaces. |
| Goal → Ralph | Partially implemented / usable by handoff | Goal prepares Ralph-owned PRD context; Ralph launch/control exists separately. The current `goal launch-ralph` surface is misleading and should be removed or replaced before being treated as done. |
| Goal → Ralph → Team(s) | Partially implemented contracts, not end-to-end done | Goal-supervised lane where Ralph owns PRD/team split and Team Admin aggregation feeds Ralph/Goal lifecycle decisions. Contracts exist; full CLI/lifecycle stitching and live dogfood proof remain. |
| Ultrawork only | Implemented baseline | Guarded launch/resume/cleanup for focused OMX Team/Ultrawork execution without wrapping it in Goal. |
| Hypergoal | Planned only | Static scaffold/template exists, but no executor or operating loop should be claimed yet. |
| Ralph → Team | Partially implemented / Ralph-owned fanout | Ralph PRD Team fanout contracts, DAG handoff artifacts, Team Admin policy, and guarded launch surfaces exist; needs clean live proof without Goal wrapping. |

Current practical strengths:
- typed runtime status reads
- typed team status / await / team-api reads
- typed adapter probe / status / envelope reads
- execution transport normalization for OMX JSON and JSONL surfaces
- adapter-tracked native Codex Goal start/status/template surfaces
- read-only Goal → Ralph handoff prompt generation
- guarded Ralph launch/resume/cleanup state control for OMX runtime workflows
- typed Ralph PRD contracts for both non-Team and Team fanout paths
- Team Admin aggregation / Ralph post-Team review / Goal lifecycle contract surfaces
- scoped Ultrawork launch/resume/cleanup state control for `omx team` workflows

## Installation for other agents

This package is **not published to PyPI yet**. Keep distribution private while the Goal/Ralph/Team operating loop is still being dogfooded.

### Install from GitHub

For another local agent or machine that has repository access:

```bash
uv tool install git+https://github.com/limhaneul12/omx-agent-adapter.git
agent-remote --help
agent-remote version
```

After install, do not prefix normal CLI usage with `uv run`. Treat `agent-remote` like any other installed executable:

```bash
agent-remote goal restore-lifecycle --goal-id <goal-id> --cwd .
agent-remote goal operating-decision --goal-id <goal-id> --team-name <team-name> --cwd .
```

For one-off execution without a persistent tool install:

```bash
uvx --from git+https://github.com/limhaneul12/omx-agent-adapter.git agent-remote --help
```

During local development inside this repository, prefer source-first execution so the CLI sees the current working tree rather than an older installed wheel:

```bash
PYTHONPATH="$PWD/src:$PWD" uv run agent-remote --help
```

Use `uv run` only inside a checked-out development repository. Installed users and other agents should run `agent-remote` directly.

### Future PyPI package

The likely public install command will be one of these after packaging, TestPyPI, and real dogfood are complete:

```bash
uv tool install agent-remote
# or, if the package is renamed before public release:
uv tool install omx-agent-adapter
```

Do not publish to PyPI until wheel build/install checks pass cleanly and the operating loop has been exercised by real agents.

## CLI quick help

For installed users and other agents:

```bash
agent-remote --help
agent-remote version
agent-remote runtime --help
agent-remote team --help
agent-remote adapt --help
agent-remote ralph --help
agent-remote ultrawork --help
agent-remote goal --help
agent-remote goal template
agent-remote goal restore-lifecycle --help
agent-remote goal operating-decision --help
```

For development from this repository, prefix with `PYTHONPATH="$PWD/src:$PWD" uv run` only when you need the current working tree:

```bash
PYTHONPATH="$PWD/src:$PWD" uv run agent-remote goal operating-decision --help
```

The current CLI is still intentionally thin, but it now exposes concrete runtime/team/history/adapt/control subcommands instead of only descriptive top-level text. The main value still lives in the importable Python surfaces under `src/`.

## Operating route guide

Documentation retention/status policy lives in [`docs/README.md`](docs/README.md).

Canonical lane/status details live in [`docs/project-operating-lanes-status.md`](docs/project-operating-lanes-status.md).

Choose one of the six top-level lanes before acting. The distinction between `Goal → Ralph → Team(s)` and `Ralph → Team` matters: the former is Goal-supervised lifecycle work, while the latter is Ralph-owned fanout without wrapping the task as a Goal.

```text
1. Goal only
   Small, clear Codex Goal objective loop.
   Done baseline: `agent-remote goal start`, `goal status`, and `goal template` exist.

2. Goal → Ralph
   Use when Goal needs Ralph to own PRD shaping, implementation planning, or single-owner execution.
   Done baseline: read-only `goal prepare-ralph` handoff and Ralph launch/control surfaces exist.
   Not done: the current `goal launch-ralph` command is too narrow/misleading and should not be used as proof of the lane.

3. Goal → Ralph → Team(s)
   Use when Goal needs lifecycle supervision and Ralph must split independent worker ownership through Team.
   Done baseline: typed PRD fanout contracts, Team worker assignments, Team Admin aggregation, Ralph post-Team review, and Goal lifecycle contracts exist.
   Not done: one clean CLI/lifecycle path and live dogfood proof across the full route.

4. Ultrawork only
   Use for focused deep-work execution through OMX Team/Ultrawork without wrapping the task in Goal.
   Done baseline: guarded `ultrawork launch`, `ultrawork resume`, and `ultrawork cleanup-stale` exist.

5. Hypergoal
   Future long-work concept that may combine Goal-level objective management with Ultrawork-style deep checkpoints.
   Done baseline: static `hypergoal template` only.
   Not done: executor, runtime state, or lifecycle loop.

6. Ralph → Team
   Use when Ralph already owns the task and needs Team fanout directly, without a Goal lifecycle envelope.
   Done baseline: typed Ralph PRD fanout contracts, Team DAG/handoff artifact helpers, Team Admin policy fields, and Ralph Team launch guardrails exist.
   Not done: clean live proof and status/readiness UX specific to this lane.
```

This is intentionally not `goal draft`: the CLI does not infer files, choose routes automatically, or auto-fanout. Agent behavior should be: choose the lane explicitly, read state/evidence first, then mutate only through the lane's proven guardrails.

## Safe live verification examples

```bash
omx state list-active --json
omx team status missing-team --json
omx team api read-monitor-snapshot --input '{"team_name":"missing-team"}' --json
omx adapt hermes probe --json
```

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run pyrefly check src
```
