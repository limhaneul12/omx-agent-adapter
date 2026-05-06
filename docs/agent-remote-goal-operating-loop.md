# Agent Remote Goal Operating Loop

## 0. Why this exists

`agent-remote` is an **agent-facing cockpit/harness for OMX**. It is not a replacement runtime for OMX, Ralph, or Team.

The Goal/Ralph/Team work in this repository exists to solve one practical problem:

```text
Agents can call many OMX commands, but they need a safe operating loop for deciding:
- what state to read first,
- what evidence is missing,
- whether review is required,
- whether mutation is safe,
- and what the next action should be.
```

The operating loop keeps OMX/Ralph/Team artifacts as source of truth and lets `agent-remote` derive typed recommendations from those artifacts.

## 1. Golden rule

```text
restore durable state
→ ask for operating-decision
→ run read-only recommended evidence commands
→ derive exactly one next artifact/action
→ verify
→ repeat
```

Never jump straight to mutation when `safe_to_mutate=false` or `requires_review=true`.

## 2. Prerequisites

Run from the actual repo root:

```bash
cd /Users/imhaneul/Documents/sky_document/project/omx-agent-adapter
```

Before changing code, read the repo rules:

```text
AGENTS.md
docs/rules/type-development-rules.md
docs/rules/schema-boundary-rules.md
docs/rules/pydantic/README.md
docs/rules/naming-rules.md
```

Useful status checks:

```bash
git status --short
git rev-list --left-right --count origin/main...HEAD
uv run agent-remote version
omx status
omx doctor --team
```

During local development, prefer source-first CLI execution:

```bash
PYTHONPATH="$PWD/src:$PWD" uv run agent-remote ...
```

Why: a plain installed console entrypoint can point at an older installed package while the working tree contains newer unpushed code.

## 3. Hermes skill usage

A local Hermes skill exists for this workflow:

```text
agent-remote-goal-operating-loop
```

Path:

```text
~/.hermes/skills/software-development/agent-remote-goal-operating-loop/SKILL.md
```

Load it in future Hermes sessions before continuing this class of work:

```text
/skill agent-remote-goal-operating-loop
```

or from CLI:

```bash
hermes -s agent-remote-goal-operating-loop
```

Use it together with:

```text
omx-agent-adapter-conventions
test-driven-development
oh-my-codex
```

## 4. A-Z usage flow

### A. Identify the goal

You need a `goal_id`. It usually comes from one of these places:

```text
.agent-remote/state/goal-lifecycle/<goal-id>.json
agent-remote goal status
previous commit/session notes
```

If no durable lifecycle artifact exists yet, do not invent a lifecycle state. Start/prepare the Goal/Ralph path first using the existing Goal surfaces.

### B. Restore lifecycle state

```bash
PYTHONPATH="$PWD/src:$PWD" uv run agent-remote goal restore-lifecycle \
  --goal-id <goal-id> \
  --cwd .
```

Expected fields:

```text
ready_to_resume
next_resume_target
bundle.goal_id
bundle.aggregation_report
bundle.ralph_review_result
bundle.lifecycle_decision
```

If `ready_to_resume=false`, stop and inspect why. Do not continue by guessing.

### C. Ask for the operating decision

```bash
PYTHONPATH="$PWD/src:$PWD" uv run agent-remote goal operating-decision \
  --goal-id <goal-id> \
  --team-name <team-name> \
  --cwd .
```

Read these fields first:

| Field | Meaning |
| --- | --- |
| `current_stage` | Derived stage from durable lifecycle artifacts. |
| `next_action` | Recommended next agent action. |
| `safe_to_mutate` | Whether mutation is allowed without more evidence. |
| `requires_review` | Whether the agent must stop for review/human input. |
| `available_evidence` | Evidence already present in artifacts. |
| `missing_evidence` | Required evidence not yet present. |
| `recommended_commands` | Read-only OMX commands to run before the next derived decision. |
| `review_blockers` | Known blockers from review/lifecycle artifacts. |

### D. Run recommended read-only evidence commands

If `recommended_commands` is non-empty, run them before deriving the next artifact.

Typical Team evidence commands:

```bash
omx team api list-tasks --input '{"team_name":"<team-name>"}' --json
omx team api read-events --input '{"team_name":"<team-name>"}' --json
omx team api read-worker-status --input '{"team_name":"<team-name>","worker":"worker-1"}' --json
```

Important interpretation:

```text
empty tasks/events        = valid evidence, not success
unknown worker status     = valid evidence, not completion
Team API ok:true          = command contract worked, not that the Team wave succeeded
```

### E. Derive exactly one next artifact/action

Use `current_stage` to choose the next move.

| `current_stage` | What it means | Normal next move |
| --- | --- | --- |
| `team_admin_aggregation_pending` | Team Admin report is missing. | Collect Team API evidence and build/read Team Admin aggregation. |
| `ralph_post_team_review_pending` | Aggregation exists; Ralph review missing. | Run Ralph post-Team review against PRD + aggregation report. |
| `goal_lifecycle_decision_pending` | Ralph review exists; Goal lifecycle decision missing. | Build Goal lifecycle decision. |
| `goal_close_ready` | Lifecycle says close is safe. | Close only if external/user policy allows it. |
| `ralph_follow_up_ready` | Follow-up worker wave is needed. | Prepare next Ralph/Team handoff. |
| `human_review_required` | Review gate/blocker exists. | Stop and report blockers. |

After deriving one artifact, re-run `operating-decision`. Do not chain multiple mutations by memory.

### F. Verify after each slice

For code changes:

```bash
uv run pyrefly check src
uv run ruff check src tests
uv run pytest -q
```

For CLI changes:

```bash
uv run pytest tests/test_cli_entrypoint.py tests/runtime/test_goal_operating_decision.py -q
uv run pyrefly check src
uv run ruff check src tests
uv run pytest -q
```

### G. Commit/push hygiene

Before commit:

```bash
git status --short
git diff --stat
```

Commit only source/docs/tests that belong to the slice. Do not commit runtime scratch unless explicitly intended.

Common local/runtime paths that should normally stay uncommitted:

```text
.agent-remote/
.omx/state/
.omx/team/
docs/jobs/
```

Push only after full gates pass and the user approves or asks for push.

## 5. Keep/delete/prune rules

This harness should stay small. Use these objective rules before adding more features.

### Keep

Keep surfaces that demonstrably make agents safer:

```text
restore-lifecycle CLI
operating-decision CLI
safe_to_mutate
requires_review
missing_evidence
recommended_commands
Team Admin aggregation report
Ralph post-Team review result
Goal lifecycle decision
```

### Experimental / review after dogfood

Review these after 2-3 real feature runs:

```text
CodexGoalOperatingStage
CodexGoalOperatingAction
fine-grained evidence source enums
string-shaped recommended command hints
```

Keep them only if they reduce agent confusion in real use.

### Avoid for now

Do not add these without strong dogfood evidence:

```text
write-lifecycle CLI
automatic close/follow-up mutation CLI
agent-remote-owned Team scheduler
agent-remote-owned Ralph runtime replacement
automatic execution of recommended_commands
```

### Delete immediately

Delete or avoid committing:

```text
local dogfood lifecycle artifacts that are not needed for continuation
scratch Team state from failed experiments
fields/commands that are not read by tests or real dogfood
compatibility wrappers that reintroduce loose schema surfaces
```

## 6. Dogfood scoring rubric

After each real feature run, rate the operating loop:

| Question | Good signal | Bad signal |
| --- | --- | --- |
| Did it prevent unsafe mutation? | Agent read evidence before acting. | Agent ignored `safe_to_mutate`. |
| Did it clarify next action? | `next_action` matched the actual needed step. | Agent still guessed from prose. |
| Did commands help? | `recommended_commands` were run and useful. | Commands were noisy or unused. |
| Did it respect OMX? | Used native OMX read surfaces. | Adapter acted like replacement runtime. |
| Was it too heavy? | Added confidence with little overhead. | More ceremony than insight. |

If two real runs show a field/enum/CLI is unused, mark it for deletion or collapse.

## 7. Troubleshooting

### `No such command 'restore-lifecycle'` or stale CLI behavior

Use source-first invocation:

```bash
PYTHONPATH="$PWD/src:$PWD" uv run agent-remote goal restore-lifecycle --goal-id <goal-id> --cwd .
```

If that works, the installed package is stale.

### Missing lifecycle artifact

Check:

```bash
find .agent-remote/state/goal-lifecycle -maxdepth 1 -type f -print
```

If no artifact exists, start/prepare the Goal path first. Do not fabricate completion/review state.

### Team API returns empty data

This is valid evidence. Treat as:

```text
Team not launched, no tasks claimed, or no events recorded yet.
```

Do not treat as success.

### `safe_to_mutate=false`

Do not close, write, merge, or launch follow-up mutation. Run evidence commands or build the required review/decision artifact first.

### `requires_review=true`

Stop and surface `review_blockers`. This is an intentional gate.

## 8. Minimal command recipe

```bash
cd /Users/imhaneul/Documents/sky_document/project/omx-agent-adapter

PYTHONPATH="$PWD/src:$PWD" uv run agent-remote goal restore-lifecycle \
  --goal-id <goal-id> \
  --cwd .

PYTHONPATH="$PWD/src:$PWD" uv run agent-remote goal operating-decision \
  --goal-id <goal-id> \
  --team-name <team-name> \
  --cwd .

# Run any read-only commands listed in recommended_commands.

uv run pyrefly check src
uv run ruff check src tests
uv run pytest -q
```

## 9. Final checklist

Before saying a Goal/Ralph/Team slice is done:

- [ ] Skill loaded or workflow doc checked.
- [ ] `restore-lifecycle` was run for the relevant `goal_id`.
- [ ] `operating-decision` was run before acting.
- [ ] Recommended read-only OMX evidence commands were executed when present.
- [ ] Empty/unknown Team evidence was interpreted honestly.
- [ ] No mutation happened while `safe_to_mutate=false`.
- [ ] Review blockers were surfaced when `requires_review=true`.
- [ ] Disposable `.agent-remote/` dogfood artifacts were removed unless needed for continuation.
- [ ] Targeted/static/full gates passed.
- [ ] Commit/push status is reported clearly.
