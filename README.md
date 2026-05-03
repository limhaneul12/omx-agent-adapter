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

## CLI quick help

```bash
uv run agent-remote --help
uv run agent-remote version
```

The current CLI is intentionally thin. The main value today lives in the importable Python surfaces under `src/`.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run pyrefly check src
```
