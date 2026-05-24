# Agent Remote Command Recipes

Use `agent-remote commands` to inspect project-owned composed commands before an agent runs anything. Recipes can combine native argv, prompt files, inline prompts, Codex execution, OMX execution, and expected artifacts while keeping a typed dry-run plan available for review.

Human flow:

```bash
agent-remote commands list --cwd .
agent-remote commands show review-diff --cwd .
agent-remote run review-diff --cwd . --dry-run
agent-remote run review-diff --cwd . --dry-run --json
```

Agent JSON contract example from `agent-remote commands list --cwd . --json`:

```json
{
  "commands": [
    {
      "id": "review-diff",
      "qualified_id": "builtin:review-diff",
      "source": "builtin",
      "description": "Review the current git diff against repository rules.",
      "risk": "read_only",
      "step_count": 1
    },
    {
      "id": "verify-handoff",
      "qualified_id": "builtin:verify-handoff",
      "source": "builtin",
      "description": "Run repo verification gates and prepare a handoff artifact.",
      "risk": "read_only",
      "step_count": 4
    },
    {
      "id": "ultragoal-roadmap",
      "qualified_id": "builtin:ultragoal-roadmap",
      "source": "builtin",
      "description": "Plan an OMX UltraGoal run from a roadmap brief file.",
      "risk": "launches_runtime",
      "step_count": 1
    }
  ],
  "builtin_count": 3,
  "repo_count": 0,
  "warnings": []
}
```

Dry-run plan example from `agent-remote run review-diff --cwd . --dry-run --json`:

```json
{
  "command_id": "review-diff",
  "qualified_id": "builtin:review-diff",
  "source": "builtin",
  "description": "Review the current git diff against repository rules.",
  "risk": "read_only",
  "dry_run": true,
  "steps": [
    {
      "index": 1,
      "command": "codex_exec",
      "agent": null,
      "native_argv": [
        "codex",
        "exec",
        "--json",
        "--output-last-message",
        ".agent-remote/runs/review-diff/final-message.md",
        "Review the current git diff against the repository rules. Return findings, risks, and an approval recommendation."
      ],
      "prompt_file": null,
      "prompt_exists": null,
      "prompt_sha256": null,
      "inline_prompt": "Review the current git diff against the repository rules. Return findings, risks, and an approval recommendation.",
      "expected_artifacts": [
        ".agent-remote/runs/review-diff/final-message.md"
      ],
      "risk": "read_only",
      "blocked_reasons": []
    }
  ],
  "blocked_reasons": []
}
```

Safety rule: use `--dry-run` first. `agent-remote run` currently plans composed commands and can record plans; it does not silently execute native Codex/OMX mutations.
