# Custom Codex + OMX Workflow Commands

Status: dogfood execution slice for the `omx-agent-adapter` custom command layer.

This project should not mirror Codex or OMX command-for-command. The purpose is to give agents and humans a safer control surface that combines Codex, OMX, MCP, Team, Ultragoal, verification, and Alexandria memory into inspectable workflows.

## Design principles

1. **Dry-run first, execute explicitly**: every composed command must be inspectable before execution; actual runs use `--execute --autonomy agent` and durable run records.
2. **Typed artifacts**: commands should declare expected artifacts so agents can verify whether the workflow actually produced evidence.
3. **Risk labels are real**: `read_only`, `external_network`, `long_running`, `launches_runtime`, and `writes_files` tell the TUI/CLI how cautious to be.
4. **Research is validated, not trusted blindly**: evidence must be challenged for source quality, contradictions, recency, and missing facts before it becomes product direction.
5. **Interview questions come from evidence gaps**: deep interview should ask only questions that the previous research/validation pass cannot answer safely.
6. **Subagents vs Team is a routing decision**: use Codex native subagents for small in-session parallel read/review tasks; use OMX Team for durable tmux/worktree/shared-state execution.
7. **Alexandria closes the loop**: successful workflows should persist decisions, source notes, PRD links, and next commands into long-term memory.

## Refined flagship loop

The user's original idea was:

> research, verify it, deep interview, research again, ask deep interview again, write PRD, choose subagents/team, then develop.

The adapter-level version is:

```text
Evidence Intake
  -> Research Pass
  -> Evidence Critic
  -> Deep Interview from gaps
  -> Refined Research Pass
  -> Product/Architecture Interview
  -> PRD + Test Spec
  -> Staffing Router
  -> Ultragoal/Team Development
  -> Verification + Review + QA
  -> Alexandria Memory
```

### 1. Evidence Intake

Capture objective, non-goals, repository context, known sources, constraints, and ambiguity level. The command should prefer a local context artifact over ad-hoc prompt memory.

Expected artifact:

- `.agent-remote/runs/research-interview-prd/context.md`

### 2. Research Pass

Use the appropriate research lane:

- **Codex-only**: `codex --search exec` for web-enabled investigation with structured output.
- **OMX-only**: `omx autoresearch-goal` for durable professor/critic research.
- **Hybrid**: Codex search plus OMX/Alexandria memory plus repo evidence.

Expected artifact:

- `.agent-remote/runs/research-interview-prd/research-pass-1.md`

### 3. Evidence Critic

Challenge the report before asking the user anything:

- Which claims are sourced?
- Which sources are official/upstream?
- Which facts are current vs inferred?
- Which claims conflict?
- Which questions are still user-preference decisions?

Expected artifact:

- `.agent-remote/runs/research-interview-prd/evidence-critic.md`

### 4. Deep Interview from gaps

Ask only the questions that cannot be resolved from evidence. This should be powered by `$deep-interview`/`omx question` in live OMX mode, but the adapter recipe can first preview the exact question strategy.

Expected artifact:

- `.omx/context/<slug>.md` or `.agent-remote/runs/research-interview-prd/interview-1.md`

### 5. Refined Research Pass

Use the interview answers to re-run research and narrow design options.

Expected artifact:

- `.agent-remote/runs/research-interview-prd/research-pass-2.md`

### 6. Product/Architecture Interview

Ask a second, smaller interview only if the refined research leaves product/architecture tradeoffs unresolved.

Expected artifact:

- `.agent-remote/runs/research-interview-prd/interview-2.md`

### 7. PRD + Test Spec

Write a PRD, acceptance criteria, test strategy, and routing recommendation.

Expected artifacts:

- `.agent-remote/runs/research-interview-prd/prd.md`
- `.agent-remote/runs/research-interview-prd/test-spec.md`

### 8. Staffing Router

Decide execution staffing:

| Situation | Route |
| --- | --- |
| One small change, low ambiguity | single Codex executor |
| Several independent read/review lanes | Codex native subagents |
| Durable multi-story implementation | OMX Ultragoal |
| Parallel implementation with worktrees/shared tasks | OMX Team inside Ultragoal story |
| Persistence loop explicitly requested | Ralph |
| Broad high-throughput independent tasks | Ultrawork |

Expected artifact:

- `.agent-remote/runs/research-interview-prd/staffing-plan.md`

### 9. Development and verification

Default development route:

```text
Ultragoal -> optional Team -> verify-handoff-plus -> code-review -> ultraqa
```

Expected artifacts:

- `.omx/ultragoal/goals.json`
- `.omx/ultragoal/ledger.jsonl`
- `.agent-remote/runs/verify-handoff-plus/handoff.md`

### 10. Alexandria Memory

Persist what was decided and why:

- final PRD path,
- source/evidence summary,
- chosen route,
- team/subagent plan,
- verification evidence,
- next command.

## Built-in command blueprints

Custom command blueprints are available through two surfaces:

- CLI/TUI preview: `comx-agent run builtin:<command> --cwd . --dry-run --json` or `/run builtin:<command>`
- CLI actual execution: `comx-agent run builtin:<command> --cwd . --execute --autonomy agent --json`; status `succeeded` exits `0`, while `failed`, `blocked`, and `requires_agent_action` exit non-zero after emitting the typed result.
- MCP preview: register `comx-agent mcp serve --cwd "$PWD"` as repo-local `omx_agent`, then call the dedicated MCP tool such as `codex_deep_research` or `verify_handoff_plus`

MCP registration:

```bash
comx-agent mcp add omx_agent --cwd . -- comx-agent mcp serve --cwd "$PWD"
comx-agent mcp tools omx_agent --cwd . --execute --json
```

Development-tree registration:

```bash
comx-agent mcp add omx_agent --cwd . --env PYTHONPATH="$PWD/src:$PWD/src/omx_remote" --force -- \
  uv run python omx_agent_adapter_cli.py mcp serve --cwd "$PWD"
```

The MCP server is dry-run-first and returns typed plans. Flagship workflows have dedicated MCP preview tools, every built-in recipe can be previewed through `omx_agent_preview_command`, and actual execution goes through the CLI executor so run records, retries, recovery, artifact checks, secret redaction, Codex default read-only sandboxing, and shell stop semantics stay consistent.

### `codex-deep-research`

**Lane**: Codex-only
**Risk**: `external_network`
**Purpose**: structured research with web search, citations, confidence labels, and a final markdown artifact.

Use when the task needs current external evidence but does not yet need durable OMX professor/critic state.

Dogfood note: pass the research objective with `--task`; the built-in prompt includes `<task>` so dry-runs and actual executions show the concrete objective.

### `omx-autoresearch-loop`

**Lane**: OMX-only
**Risk**: `long_running`
**Purpose**: preview a durable `omx autoresearch-goal` professor/critic workflow. Completion requires a pass verdict, not just a generated report.

Use when the user wants research to be gated and resumable.

### `research-interview-prd`

**Lane**: Codex + OMX hybrid
**Risk**: `long_running`
**Purpose**: the flagship loop: validated research, evidence-gap interview, refined research, second interview if needed, PRD/test spec, staffing plan, and handoff.

Use for ambiguous product/build requests where the adapter should act like a product researcher + interviewer + architect.

### `verify-handoff-plus`

**Lane**: local + Codex review
**Risk**: `read_only`
**Purpose**: stronger final handoff gate: diff check, lint/typecheck/tests, TUI/research smokes, and Codex review prompt.

Use before checkpointing final Ultragoal evidence.

## Dogfood command family

The dogfood slice expands the built-in catalog with practical project-owned recipes, including the collaboration/research command suite. They remain preview/dry-run-first, but are now addressable by the actual executor: local/Codex/MCP steps execute, prompt-only steps write handoff artifacts and stop for agent action, and runtime-launching OMX steps are policy-gated instead of blindly started. Missing artifacts from subprocess/Codex/MCP steps are treated as failures, not placeholder success.

### Operational guardrails and closeout

| Command | Risk | Purpose |
| --- | --- | --- |
| `route-doctor` | `read_only` | Diagnose the safest Codex/OMX/project route with catalog, route policy, preflight, and next-action evidence. |
| `mcp-onboard-audit` | `read_only` | Audit Codex/comx-agent MCP registration, tool visibility, OAuth/env risk, and redaction needs. |
| `upstream-contract-refresh` | `read_only` | Run Codex/OMX probe suites and compare observed upstream contracts. |
| `skillize-workflow` | `writes_files` | Convert a validated recipe/run record into a local Codex skill with validation evidence. |
| `run-ledger-closeout` | `read_only` | Inspect `.agent-remote/runs`, verify artifacts, build replay-plan evidence, and prepare a handoff. |
| `alexandria-memory-capture` | `writes_files` | Save PRD, decisions, verification evidence, and next commands into `/Users/imhaneul/Desktop/Alexandria`. |
| `docs-sync-guardian` | `read_only` | Decide whether code changes require docs/examples/AGENTS/skill updates. |
| `dependency-incident-audit` | `external_network` | Research a dependency advisory, map repo impact, and propose safe patch/verification steps. |

### Company-style orchestration

| Command | Risk | Purpose |
| --- | --- | --- |
| `migration-checkpoint-loop` | `launches_runtime` | Split large migrations into UltraGoal checkpoints with validation gates and rollback notes. |
| `company-discovery-loop` | `long_running` | Research, evidence-critic, deep-interview, PRD/test spec, staffing, and memory summary. |
| `company-build-loop-plus` | `launches_runtime` | Accepted PRD to UltraGoal, optional Team, verification/review/UltraQA, and memory closeout. |
| `product-council` | `long_running` | PM/researcher/architect/critic decision memo with build/no-build/research-more verdict. |
| `team-sprint-plan` | `launches_runtime` | Convert a PRD or UltraGoal story into OMX Team lanes, roles, mailbox protocol, and checkpoint expectations. |
| `subagent-research-swarm` | `external_network` | Use read-heavy Codex subagent research lanes and synthesize a cited memo. |
| `ultragoal-story-factory` | `launches_runtime` | Convert PRD/test spec into UltraGoal-ready stories, acceptance criteria, verification, and handoff prompts. |
| `qa-war-room` | `long_running` | Multi-role verification war room with reviewer/QA/security/performance evidence and approve/block verdict. |
| `librarian-closeout` | `writes_files` | Verify final artifacts and save accepted decisions/evidence to the Alexandria Obsidian vault. |

For objective-driven dogfood commands, pass `--task "<objective>"`. Recipes that research, plan, or split work should include `<task>` in the first Codex prompt so `run --dry-run` previews the same objective that `run --execute` will send.


## Collaboration and research command suite

These seven commands compose OMX, Codex, Codex native-agent specialist lanes, local evidence reads, TUI previews, and Alexandria/UltraGoal handoffs into practical operator workflows. They are dry-run-first, not dry-run-only: local/Codex read-only steps can execute through `agent-remote run builtin:<command> --execute --autonomy agent --task "..." --json`, while Team/UltraGoal/runtime-spawning work remains a policy-gated handoff unless an agent-approved launch path exists. For Codex specialist lanes, dry-run plans expose both the role lane and the concrete `agent_type` override that will be used for the `codex` subprocess; this prevents a single prompt from pretending to be multiple subagents.

Alexandria is the memory/library system. The suite does not create a Codex `librarian` subagent. Use Alexandria-oriented prompt/MCP handoffs for memory search/save phases and keep memory notes summary-only with no secrets.

| Command | TUI label | Risk | Purpose |
| --- | --- | --- | --- |
| `collaboration-kickoff` | Collaboration → Kickoff | `long_running` | Turn a broad objective into route, staffing, subagent roles, UltraGoal/Team fanout advice, and a runtime handoff. |
| `team-standup-sync` | Collaboration → Team Standup Sync | `read_only` | Read Team evidence and summarize workers, blockers, proof layers, and suggested dispatches without mutating mailboxes. |
| `integration-room` | Collaboration → Integration Room | `long_running` | Integrate Team/subagent/run outputs into accepted decisions, conflict matrix, integration order, and verification plan. |
| `conflict-resolution-council` | Collaboration → Conflict Resolution Council | `long_running` | Resolve conflicting agent outputs or design options with an ADR-style decision. |
| `parallel-review-board` | Review → Parallel Review Board | `long_running` | Run specialist review lanes for security, tests, maintainability, performance, docs, and final approve/block synthesis. |
| `release-readiness-room` | Release → Release Readiness Room | `writes_files` | Compose verification, review, docs sync, run-ledger evidence, Alexandria closeout, and release verdict. |
| `idea-to-prd-council` | Research → Idea to PRD Council | `long_running` | Convert an idea into product-slug PRD/test/execution/UltraGoal artifacts with Alexandria begin/end phases and validator approval. |

CLI examples verified against the development tree:

```bash
agent-remote commands list --cwd . --json
agent-remote commands show builtin:idea-to-prd-council --cwd . --json
agent-remote run builtin:idea-to-prd-council --cwd . --dry-run --task "AI memory assistant for developers" --json
agent-remote run builtin:collaboration-kickoff --cwd . --dry-run --task "coordinate implementation" --json
agent-remote run builtin:release-readiness-room --cwd . --dry-run --task "new command suite release" --json
```

TUI usage:

```text
/commands
/run builtin:idea-to-prd-council --task "AI memory assistant for developers"
/run builtin:collaboration-kickoff --task "coordinate implementation"
```

`idea-to-prd-council` uses a product workspace at `.agent-remote/workspaces/idea-to-prd-council/<product_slug>/current/` so repeated work on the same idea updates one workspace instead of creating dated folders. Artifact names include `00_intake/idea.md`, `01_memory/similar_ideas.md`, `02_research/evidence_ledger.md`, `04_prd/prd.md`, `04_prd/test_spec.md`, `04_prd/execution_plan.md`, `05_validation/validation_verdict.md`, and `06_ultragoal/ultragoal_brief.md`. The final UltraGoal step is a policy-gated handoff and may surface a recoverable missing generated-brief blocker in dry-run until earlier prompt/Codex phases materialize the brief.

## Future schema extensions

The first slice can use existing `CommandRecipe` and `CommandStep` fields. Later improvements should add:

- command variables (`topic`, `slug`, `rubric`, `prd_path`),
- stage labels (`research`, `interview`, `prd`, `execution`, `verification`, `memory`),
- explicit approval policy,
- Codex option fields (`search`, `sandbox`, `model`, `output_schema`),
- explicit step kinds for `omx_autoresearch_goal`, `omx_code_review`, and `omx_ultraqa`,
- research citation/source-quality contracts.
