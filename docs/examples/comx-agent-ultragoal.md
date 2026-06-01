# Agent Remote UltraGoal

UltraGoal is native OMX. `comx-agent` exposes status/capability evidence and command-recipe planning around UltraGoal, but it does not revive the removed project-owned HyperGoal lane.

Human flow:

```bash
comx-agent ultragoal status --cwd .
comx-agent commands show builtin:implementation-kickoff --cwd .
comx-agent run builtin:implementation-kickoff --cwd . --dry-run --json
comx-agent route recommend --task "turn this roadmap into durable multi-goal work" --cwd .
```

Agent JSON contract example from `comx-agent ultragoal status --cwd . --json`:

```json
{
  "state": "available",
  "supported": true,
  "capability_command": [
    "ultragoal",
    "--help"
  ],
  "capability_result": {
    "exit_code": 0,
    "stdout": "omx ultragoal - Durable repo-native multi-goal workflow over Codex goal mode",
    "stderr": ""
  },
  "status_command": [
    "ultragoal",
    "status",
    "--json"
  ],
  "status_result": {
    "exit_code": 0,
    "stdout": "{\"summary\":{\"activeGoalId\":\"G010-human-and-agent-ux-documentation\"}}",
    "stderr": ""
  },
  "cwd": ".",
  "warnings": []
}
```

Cockpit capability excerpt from `comx-agent cockpit snapshot --cwd . --json`:

```json
{
  "active_runtime_modes": [
    "ultragoal"
  ],
  "status_sources": [
    {
      "name": "capabilities",
      "status": "observed",
      "detail": "Codex available=True; OMX available=True.",
      "evidence_path": null
    },
    {
      "name": "route_policy",
      "status": "observed",
      "detail": "Route recommendations are derived from capabilities, config, recipes, and runtime safety evidence.",
      "evidence_path": null
    }
  ],
  "capabilities": {
    "omx": {
      "name": "omx",
      "available": true,
      "executable_path": "/opt/homebrew/bin/omx",
      "version": "oh-my-codex v0.18.2",
      "commands": [
        {
          "name": "ultragoal",
          "available": true,
          "detail": "omx ultragoal --help succeeded."
        }
      ],
      "warnings": []
    }
  }
}
```

Operating rule: durable roadmap execution belongs to OMX UltraGoal. Project-owned composition belongs to `commands`, `run`, `route`, `preflight`, and `runs` surfaces.
