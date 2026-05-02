# omx-agent-adapter

Agent-facing adapter layer for operating OMX as a stateful runtime.

## Current implementation highlights

- Execution transport parsing stays separate from normalization and contract promotion.
- Execution contracts currently cover message, output text, tool call, and tool result events.
- Tool interactions can be grouped into matched, duplicate, unmatched, and missing-result surfaces.
- Runtime status is normalized into typed mode snapshots plus anomaly reporting.

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run pyrefly check src
```
