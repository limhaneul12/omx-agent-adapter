# agent-remote

Agent-facing adapter layer for operating OMX as a stateful runtime.

## What this repo is good for

This project is currently most useful as a **type-safe Python wrapper around structured OMX surfaces**.
It gives agents and Python callers a more stable interface than calling raw OMX commands and re-parsing each payload at every call site.

Current practical strengths:
- typed runtime status reads
- typed team status / await / team-api reads
- typed adapter probe / status / envelope reads
- execution transport normalization for OMX JSON and JSONL surfaces
- guarded Ralph launch/resume/cleanup state control for OMX runtime workflows
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
