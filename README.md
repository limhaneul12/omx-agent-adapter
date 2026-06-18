# comx-agent

Agent-facing control layer that helps agents use **OMX + Codex strongly** through typed, inspectable operating routes.

## What this repo is for

`comx-agent` is not just a thin wrapper around raw OMX commands. The project direction is to make agents better at operating the Codex/OMX stack by giving them route selection language, typed state, safe evidence collection, runtime guardrails, and lifecycle artifacts.

The intended top-level operating lanes are intentionally small and fixed:

| Lane | Status | Meaning |
| --- | --- | --- |
| Goal only | Implemented baseline | Native Codex Goal objective loop with adapter-tracked mirror state, status, and template surfaces. |
| Goal → Ralph | Partially implemented / usable by handoff | Goal prepares Ralph-owned PRD context through `goal prepare-prd-prompt`; Ralph launch/control exists separately under `comx-agent ralph`. |
| Goal → Ralph → Team(s) | Partially implemented contracts, not end-to-end done | Goal-supervised lane where Ralph owns PRD/team split and Team Admin aggregation feeds Ralph/Goal lifecycle decisions. Contracts exist; full CLI/lifecycle stitching and live dogfood proof remain. |
| Ultrawork only | Implemented baseline | Guarded launch/resume/cleanup for focused OMX Team/Ultrawork execution without wrapping it in Goal. |
| UltraGoal | Native OMX + composition baseline | Native OMX UltraGoal status/capability is exposed through `comx-agent ultragoal status`; broader command composition lives under recipes, not a project-owned HyperGoal lane. |
| Ralph → Team | Partially implemented / Ralph-owned fanout | Ralph PRD Team fanout contracts, DAG handoff artifacts, Team Admin policy, and guarded launch surfaces exist; needs clean live proof without Goal wrapping. |

Current practical strengths:
- typed runtime status reads
- typed team status / await / team-api reads
- typed adapter probe / status / envelope reads
- execution transport normalization for OMX JSON and JSONL surfaces
- repo-scoped cockpit snapshots with capability, route, recipe, PR, and runtime evidence
- adapter-tracked native Codex Goal start/status/template surfaces
- read-only Goal → Ralph handoff prompt generation
- guarded Ralph launch/resume/cleanup state control for OMX runtime workflows
- typed Ralph PRD contracts for both non-Team and Team fanout paths
- Team Admin aggregation / Ralph post-Team review / Goal lifecycle contract surfaces
- scoped Ultrawork launch/resume/cleanup state control for `omx team` workflows
- native OMX UltraGoal capability/status reads through `comx-agent ultragoal status`
- repo-local TOML subagent config validation/list/show and Codex native-agent materialization planning via `comx-agent agents`
- typed project-owned command catalog, dry-run planning, and actual policy-gated execution via `comx-agent commands` / `comx-agent run --dry-run` / `comx-agent run --execute --autonomy agent`
- collaboration/research command suite for kickoff, standup, integration, conflict resolution, review board, release readiness, and idea-to-PRD handoff workflows
- reusable preflight reports for command/route/prompt safety via `comx-agent preflight`
- route recommendations and blocked alternatives via `comx-agent route`
- recorded dry-run and actual run plans, attempts, stdout/stderr, artifacts, recovery evidence, and handoff artifacts via `comx-agent runs`
- upstream Codex/OMX command contract probes via `comx-agent probes`

## Installation for other agents

This package is **not published to PyPI yet**. Keep distribution private while the Goal/Ralph/Team operating loop is still being dogfooded.

### Install from GitHub

For another local agent or machine that has repository access:

```bash
uv tool install git+https://github.com/limhaneul12/omx-agent-adapter.git
comx-agent --help
comx-agent --help
comx-agent version
comx-agent version
```

After install, do not prefix normal CLI usage with `uv run`. Treat `comx-agent` like any other installed executable:

```bash
comx-agent goal restore-lifecycle --goal-id <goal-id> --cwd .
comx-agent goal operating-decision --goal-id <goal-id> --team-name <team-name> --cwd .
```

For one-off execution without a persistent tool install:

```bash
uvx --from git+https://github.com/limhaneul12/omx-agent-adapter.git comx-agent --help
```

During local development inside this repository, prefer source-first execution so the CLI sees the current working tree rather than an older installed wheel:

```bash
PYTHONPATH="$PWD/src:$PWD" uv run comx-agent --help
```

Use `uv run` only inside a checked-out development repository. Installed users and other agents should run `comx-agent` directly.

### Future PyPI package

The likely public install command will be one of these after packaging, TestPyPI, and real dogfood are complete:

```bash
uv tool install comx-agent
# or, if the package is renamed before public release:
uv tool install omx-agent-adapter
```

Do not publish to PyPI until wheel build/install checks pass cleanly and the operating loop has been exercised by real agents.

## Command composition quickstart

Use this flow when a human or agent needs to choose, inspect, plan, and record a composed Codex/OMX command:

```bash
comx-agent agents validate --cwd .
comx-agent cockpit snapshot --cwd .
comx-agent route recommend --task "review current diff" --cwd .
comx-agent commands list --cwd . --json
comx-agent commands show builtin:company-run --cwd . --json
comx-agent preflight run builtin:review-gate --cwd . --json
comx-agent run builtin:review-gate --cwd . --dry-run
comx-agent run builtin:review-gate --cwd . --dry-run --json --record-run
comx-agent run builtin:discovery-gate --cwd . --dry-run --task "clarify a company-run idea" --json
comx-agent run builtin:research-brief --cwd . --dry-run --task "current upstream evidence" --json
comx-agent run builtin:idea-to-prd --cwd . --dry-run --task "turn this idea into a PRD" --json
comx-agent run builtin:implementation-kickoff --cwd . --dry-run --task "coordinate implementation" --json
comx-agent run builtin:company-run --cwd . --dry-run --task "build an agent company" --json
comx-agent run builtin:company-run --cwd . --execute --autonomy agent --task "build an agent company" --model gpt-5.5 --xhigh --json
comx-agent run 'builtin:adapter-ops mcp-audit' --cwd . --dry-run --task "audit MCP setup" --json
comx-agent runs handoff <run-id> --cwd .
```

Runtime options can be set per invocation instead of through environment variables:

- `--model <model>` passes an explicit Codex model to Codex-backed recipe steps and company-run council lanes.
- `--reasoning-effort low|medium|high|xhigh` passes `model_reasoning_effort` to Codex.
- `--xhigh` is a shorthand for `--reasoning-effort xhigh`.
- `--madmax` is dangerous: it implies xhigh reasoning and passes Codex approval/sandbox bypass to Codex-backed steps. Use it only when that risk is intended.

For live `company-run` Team fanout, these options are also recorded in company-run artifacts and forwarded to OMX Team workers through a transient adapter-owned subprocess environment override; users do not need to set `OMX_TEAM_WORKER_LAUNCH_ARGS` manually. The company-run worker dispatch artifact also recommends per-worker reasoning effort (`medium`, `high`, or `xhigh`) from each lane's expected ambiguity and risk so Team handoffs do not default every worker to the same thinking depth.

Useful adjacent surfaces:

```bash
comx-agent probes run omx-basic --cwd . --json
comx-agent agents plan-apply-codex --cwd . --json
comx-agent agents codex-status --cwd . --json
comx-agent ultragoal status --cwd . --json
comx-agent surface --cwd . --json
comx-agent mcp servers --cwd . --json
comx-agent mcp tools <server-name> --cwd . --json
comx-agent mcp call <server-name> <tool-name> --arguments-json '{}' --execute --json
```

## MCP client and command surfaces

The adapter-owned workflow recipes now expose exactly ten public workflow commands plus a separate maintenance namespace:

| Group | Command id | Risk |
| --- | --- | --- |
| Lifecycle | `route-next` | `read_only` |
| Lifecycle | `discovery-gate` | `long_running` |
| Lifecycle | `research-brief` | `external_network` |
| Lifecycle | `idea-to-prd` | `long_running` |
| Lifecycle | `implementation-kickoff` | `launches_runtime` |
| Lifecycle | `team-sync` | `read_only` |
| Lifecycle | `integration-plan` | `long_running` |
| Lifecycle | `review-gate` | `long_running` |
| Lifecycle | `release-readiness` | `writes_files` |
| Macro | `company-run` | `launches_runtime` |
| Adapter Ops | `adapter-ops mcp-audit` | `read_only` |
| Adapter Ops | `adapter-ops contract-refresh` | `read_only` |
| Adapter Ops | `adapter-ops skillize` | `writes_files` |
| Adapter Ops | `adapter-ops run-ledger` | `read_only` |
| Adapter Ops | `adapter-ops memory-capture` | `writes_files` |

These are not raw aliases: they preview staged Codex/OMX/local/MCP steps, risk level, expected artifacts, typed role lanes, Codex native-agent bindings, root `prompt/` Markdown assets, and handoff points before any runtime launch. `discovery-gate` is an adapter-owned pre-planning gate that can hand off to OMX `deep-interview` without exposing a duplicate adapter command. `company-run` is a build-oriented macro orchestration mode: it records Gate -1 memory/context recovery, Gate 0 discovery/ROI/no-build, internal research/proceed decision records, PRD readiness, implementation-kickoff as the development-start gate, Team plus subagents, review/release loops, user-facing decision reports, and Alexandria MCP tool points for memory recall, librarian queries, artifact curation, context recovery, and closeout. Completed Team execution is treated as worker-output evidence, not automatic release readiness; leader-owned integration/review synthesis remains required.

`comx-agent surface` separates direct **native commands** from **composed commands** loaded from the built-in/repo recipe catalog.

MCP support is client/consumer-only: `comx-agent mcp` can read Codex's MCP registry via `codex mcp list --json`, read repo-local MCP config from `.comx-agent.toml`, list server tools, and execute a tool only when `--execute` is passed. The adapter does not expose its own MCP server; use `comx-agent commands show` and `comx-agent run --dry-run` as the primary preview surfaces.

Register an external MCP server repo-locally:

```bash
comx-agent mcp add local_docs --cwd . -- uvx example-mcp-server
comx-agent mcp tools local_docs --cwd . --execute --json
comx-agent mcp call local_docs search --arguments-json '{"query":"release checklist"}' --execute --json
```

During local development, keep MCP registration pointed at the external server command you want to consume:

```bash
comx-agent mcp add local_docs --cwd . --force -- uv run docs-mcp --cwd "$PWD"
```

MCP calls are dry-run-first from the adapter side: `comx-agent mcp call` previews the resolved server, tool, and arguments until `--execute` is passed.

The human-readable commands explain the route and risk. The `--json` surfaces provide typed fields, stable enums, artifact paths, warnings, blockers, and exit codes for automated agents.

Tracked examples:

- [`docs/examples/comx-agent-command-recipes.md`](docs/examples/comx-agent-command-recipes.md)
- [`docs/examples/comx-agent-route-recommendations.md`](docs/examples/comx-agent-route-recommendations.md)
- [`docs/examples/comx-agent-run-records.md`](docs/examples/comx-agent-run-records.md)
- [`docs/examples/comx-agent-subagents-toml.md`](docs/examples/comx-agent-subagents-toml.md)
- [`docs/examples/comx-agent-ultragoal.md`](docs/examples/comx-agent-ultragoal.md)

## CLI quick help

For installed users and other agents:

```bash
comx-agent --help
comx-agent --help
comx-agent version
comx-agent version
comx-agent runtime --help
comx-agent cockpit --help
comx-agent team --help
comx-agent history --help
comx-agent adapt --help
comx-agent agents --help
comx-agent commands --help
comx-agent preflight --help
comx-agent surface --help
comx-agent mcp --help
comx-agent probes --help
comx-agent route --help
comx-agent runs --help
comx-agent run --help
comx-agent prd --help
comx-agent ralph --help
comx-agent ultrawork --help
comx-agent ultragoal --help
comx-agent goal --help
comx-agent goal template
comx-agent goal restore-lifecycle --help
comx-agent goal operating-decision --help
```

For development from this repository, prefix with `PYTHONPATH="$PWD/src:$PWD" uv run` only when you need the current working tree:

```bash
PYTHONPATH="$PWD/src:$PWD" uv run comx-agent goal operating-decision --help
```

The current CLI is still intentionally thin, but it now exposes concrete runtime/team/history/adapt/control subcommands instead of only descriptive top-level text. The main value still lives in the importable Python surfaces under `src/`.

## Operating route guide

The concise operating-route summary lives in this section. Longer historical lane/status docs were intentionally retired; use this README and `docs/rules/` as the current navigation surface.

Choose one of the six top-level lanes before acting. The distinction between `Goal → Ralph → Team(s)` and `Ralph → Team` matters: the former is Goal-supervised lifecycle work, while the latter is Ralph-owned fanout without wrapping the task as a Goal.

```text
1. Goal only
   Small, clear Codex Goal objective loop.
   Done baseline: `comx-agent goal start`, `goal status`, and `goal template` exist.

2. Goal → Ralph
   Use when Goal needs Ralph to own PRD shaping, implementation planning, or single-owner execution.
   Done baseline: read-only `goal prepare-prd-prompt` handoff and Ralph launch/control surfaces exist.

3. Goal → Ralph → Team(s)
   Use when Goal needs lifecycle supervision and Ralph must split independent worker ownership through Team.
   Done baseline: typed PRD fanout contracts, Team worker assignments, Team Admin aggregation, Ralph post-Team review, and Goal lifecycle contracts exist.
   Not done: one clean CLI/lifecycle path and live dogfood proof across the full route.

4. Ultrawork only
   Use for focused deep-work execution through OMX Team/Ultrawork without wrapping the task in Goal.
   Done baseline: guarded `ultrawork launch`, `ultrawork resume`, and `ultrawork cleanup-stale` exist.

5. UltraGoal
   Use native OMX UltraGoal for durable multi-goal roadmaps instead of the removed project-owned HyperGoal scaffold.
   Done baseline: `comx-agent ultragoal status` reads native OMX capability/status; command recipes, route policy, cockpit capability evidence, and run records make UltraGoal-oriented command composition discoverable.
   Done executor slice: `comx-agent run --execute --autonomy agent` can record actual runs and policy-gated handoffs. Native durable roadmap execution still belongs to OMX UltraGoal; runtime-spawning recipe steps are guarded and recorded instead of silently launched.

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
comx-agent cockpit snapshot --cwd . --json
comx-agent route recommend --task "review current diff" --cwd . --json
comx-agent run builtin:review-gate --cwd . --dry-run --json
```

## Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run pyrefly check src
```
ㅁㄴㅇㅁㄴㅇㅁㄴdasdasㅇㅁㄴㅇ