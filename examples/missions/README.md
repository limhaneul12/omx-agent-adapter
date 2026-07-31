# Mission request examples

These files are strict `mission-request.v1` templates for the shared GUI, CLI,
and Agent Mission service.

Before execution:

1. Copy the closest template.
2. Replace `mission_id` with a unique stable identifier. Reusing an identifier
   with a different request is rejected.
3. Set `workspace` to the intended workspace path, or run from that workspace
   with `workspace` left as `.`.
4. Run plan and validation before execution.

```bash
uv run comx-agent agent plan-mission mission.json
uv run comx-agent agent validate-mission mission.json
uv run comx-agent agent execute-mission mission.json
```

Mission execution is detached by default. Observe the same durable Mission and
Strategy state with:

```bash
uv run comx-agent agent mission-status /absolute/workspace MISSION_ID
uv run comx-agent agent mission-events /absolute/workspace MISSION_ID
uv run comx-agent agent mission-artifacts /absolute/workspace MISSION_ID
```

## Profiles

- `codex-readonly.json`: one native Codex Run in a read-only sandbox.
- `omx-readonly.json`: one native OMX Run in a read-only sandbox.
- `codex-then-omx-review.json`: Codex execution, OMX artifact review, verified
  blocker gate, and conditional Codex resume.

The cross-provider profile requires `mutation_allowed=true` and a writable
sandbox because OMX must write the harness-owned
`.comx-agent/v2/mission-artifacts/<mission-id>/blockers.json` evidence file.
Its example objective still forbids project source modification. Use an isolated
Git worktree for the first live dogfood run.

Every template denies commit and push. `comx-agent` records local Git evidence,
but local state cannot prove a rejected or no-op push attempt. Provider
installation, parser compatibility, and login probes are not substitutes for a
successful live Mission.
