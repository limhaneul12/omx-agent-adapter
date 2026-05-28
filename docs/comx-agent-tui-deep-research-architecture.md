# comx-agent TUI Deep Research Architecture

Status: design source for the Codex + OMX TUI expansion after G002 research.

This document turns the G002 evidence packet into the product and implementation shape for `comx-agent`. It should guide the next implementation story rather than replace the repository rules in `AGENTS.md` or `docs/rules/`.

## Objective

`comx-agent` should become a typed terminal cockpit for using Codex + OMX together. It should remain an adapter/control surface, not a new agent framework. The TUI must serve two operators:

1. **Agents**: need stable JSON/state contracts, route guidance, safe dry-runs, evidence capture, MCP visibility, Team/Ultragoal checkpoint help, and reproducible commands.
2. **Humans**: need a Codex-like terminal surface with slash commands, status panels, sessions, MCP/tool browsing, command recipes, and guarded workflow launchers.

The goal is not to clone every Codex or OMX internal detail. The goal is to expose the combined workflow in a way that makes the correct next action obvious and auditable.

## Evidence inputs

G002 research artifacts are kept under `.omx/reports/tui-deep-research-team/`:

- `worker-1-codex-tui.md` — Codex CLI/TUI slash commands, sessions/history, approvals, MCP panels, multi-agent UX.
- `worker-2-codex-mcp.md` — Codex MCP registry/config/tool UX and comparison to this repo.
- `worker-3-omx-ux.md` — installed OMX Team, Ultragoal, HUD, worker/mailer/state runtime UX.
- `worker-4-comx-gaps.md` — current `comx-agent` surfaces and implementation gaps.
- `leader-codex-omx-synthesis.md` — cross-lane synthesis and implementation direction.

Key upstream anchors:

- OpenAI Codex clone at `/tmp/omx-agent-adapter-tui-research/codex`, commit `b637fd26aa4cb3ac6610613747e62901e9921c3b`.
- Installed OMX `0.18.4` under `/opt/homebrew/lib/node_modules/oh-my-codex/dist` and plugin skills under `/Users/imhaneul/.codex/plugins/cache/oh-my-codex-local/oh-my-codex/0.18.4/skills`.
- Official docs checked: Codex CLI slash commands, Codex MCP, and OpenAI Deep Research guide.

## Product stance

`comx-agent` should present itself as:

> A Codex/OMX control cockpit that shows the native Codex and OMX surfaces, adds typed repo-local command recipes, and creates durable research/build/evidence workflows.

Non-goals:

- Do not become a replacement for Codex, OMX, Ralph, Team, Ultrawork, or MCP.
- Do not hide the underlying command that will run.
- Do not treat every prompt as executable by default.
- Do not collapse raw transport parsing, routing/normalization, and stable schema validation into one layer.

## Concept mapping

| Source concept | Codex/OMX behavior | comx-agent TUI representation |
| --- | --- | --- |
| Codex slash command catalog | Ordered commands with descriptions, inline args, and active-task availability | Typed `ComxTuiCommand` catalog and slash palette |
| Codex `/mcp` | Server/tool inventory and verbose diagnostics | `/mcp` registry panel, `/mcp tools <server>`, redacted diagnostics |
| Codex sessions/history | Resume/fork pickers, history JSONL, transcript preview | `/sessions`, `/session`, eventual resume/fork panel over `.comx-agent/sessions` |
| Codex approvals | Explicit accept/cancel/session/policy amendment decisions | Mutating command intent preview + approval gate |
| Codex multi-agent UX | `/agent` picker and agent status rows | Team/subagent worker board with role, task, pane, worktree, mailbox state |
| OMX HUD | Runtime statusline for active modes | Top status strip and `/status` panel |
| OMX Team | Durable tmux/worktree/task/mailbox runtime | `/team` board with task counts, claims, panes, inbox/dispatch state |
| OMX Ultragoal | Durable stories, ledger, checkpoints | `/ultragoal` panel with current story, evidence requirements, checkpoint command |
| OMX skills | Workflow entrypoints such as deep-interview, ralplan, ultragoal, code-review, ultraqa | `/interview`, `/research`, `/plan`, `/verify` workflow recipes that explain the underlying skill/command |
| Alexandria | Long-memory context vault and librarian workflows | Optional memory status and context-note capture in research artifacts |

## Runtime architecture

The TUI should be a thin interactive layer over importable runtime modules.

```text
src/omx_remote/
├── cli_launcher/
│   └── comx_cli.py                  # Typer + prompt-toolkit shell only
├── runtime/
│   ├── comx/
│   │   ├── tui_command_catalog.py   # ordered slash command definitions
│   │   ├── tui_command_router.py    # routes parsed commands to runtime readers/planners
│   │   ├── tui_renderer.py          # frame rendering from schemas only
│   │   ├── tui_session_store.py     # durable TUI session records
│   │   └── research_workflow.py     # staged research/interview/verification plan artifacts
│   ├── mcp/                         # existing MCP registry/tool client stays here
│   ├── next/                        # safe next-action reader
│   ├── commands/                    # command recipes and dry-run plans
│   └── cockpit/                     # existing lane evidence readers
└── schemas/
    └── comx/
        ├── tui_schemas.py           # frame/session display schemas
        ├── tui_command_schemas.py   # split if command catalog grows
        └── research_workflow_schemas.py
```

Layer rules:

1. CLI collects input and prints output.
2. Command catalog normalizes slash command text and metadata.
3. Router calls existing runtime modules and returns typed display/results.
4. Runtime modules own transport parsing and raw boundaries.
5. Renderer consumes stable schemas only.

## Slash command model

Each command should carry:

- name and aliases,
- presentation group and order,
- description,
- whether inline args are supported,
- read-only vs mutating intent,
- whether available during active work,
- optional underlying command/recipe hint,
- handler id for the router.

Initial command set:

| Command | Purpose | Default safety |
| --- | --- | --- |
| `/help` | command help | read-only |
| `/status` | full cockpit status | read-only |
| `/surface` | native/composed command inventory | read-only |
| `/commands` | recipe list | read-only |
| `/run <recipe>` | dry-run recipe plan; explicit execute later | dry-run |
| `/route <prompt>` | classify route/lane | read-only |
| `/next` | safe next action | read-only |
| `/mcp` | registry panel | read-only |
| `/mcp verbose` | detailed redacted diagnostics | read-only |
| `/mcp tools <server>` | tool inventory | read-only network/stdio connect |
| `/mcp call <server> <tool>` | tool call preview | dry-run unless explicit execute path is added |
| `/session` | current TUI session | read-only |
| `/sessions` | session list | read-only |
| `/team` | active Team board | read-only by default |
| `/ultragoal` | current Ultragoal story/ledger/checkpoint guidance | read-only |
| `/goal` | active Codex goal state | read-only by default |
| `/interview` | create/continue clarification plan | artifact write |
| `/research` | create staged research workflow artifact | artifact write |
| `/clear` | redraw | local UI |
| `/quit` `/exit` | save and exit | local UI |

Mutating commands should be explicit and previewed. For example, `/team shutdown <team>` should render a plan before running; `/mcp call --execute` should be deliberately separate from `/mcp call`.

## Display surfaces

### Top status strip

Show compact, always-visible state:

- model label,
- workspace and branch,
- permission/sandbox label,
- next-action state,
- active Codex goal state,
- Ultragoal story id/status,
- Team worker/task counts,
- warnings count.

This should consume existing `NextActionResult`, cockpit snapshots, and OMX status/HUD outputs where available.

### Cockpit panel

`/status` should show:

- native command count and composed command count,
- active modes,
- current G/O story if `.omx/ultragoal` exists,
- team summaries from `omx team status --json` when active,
- latest warnings and blocked actions,
- useful commands to run next.

### MCP panel

`/mcp` should show rows with:

- source (`codex`, `repo`, future `plugin` if distinct),
- qualified name,
- enabled/disabled status and reason,
- auth status,
- transport kind,
- redacted target,
- startup/tool timeouts,
- warnings,
- tool-list action hint.

Redaction is mandatory by default for env values, headers, bearer tokens, and secret-like key names. The UI may show variable names and “present/missing”.

### Team panel

`/team` should show:

- team name, phase, workspace mode,
- worker panes and worktrees,
- dead/non-reporting counts,
- task totals,
- per-task owner, claim owner, lease expiry, dependencies, result/error preview,
- mailbox/dispatch warnings,
- Ultragoal checkpoint guidance if present.

Use `omx team status --json` and `omx team api` outputs instead of parsing tmux where possible. `omx sparkshell --tmux-pane` remains an inspect action, not the primary data source.

### Ultragoal panel

`/ultragoal` should show:

- goals file path and ledger path,
- current story id/title/objective/status,
- aggregate Codex goal objective/status if available,
- checkpoint template and evidence requirements,
- final-story vs intermediate-story warning,
- last checkpoint evidence summary.

## Deep interview + research workflow

The user’s idea should become a staged workflow, not a monolithic black box.

```text
intake
  -> ambiguity scan
  -> optional deep interview questions
  -> source/MCP policy
  -> research plan
  -> evidence collection
  -> verification/critic pass
  -> artifact synthesis
  -> optional Ultragoal/Team handoff
```

A `/research` command should create a local artifact under `.comx-agent/research/` or a configured artifact directory with:

- research id,
- user objective,
- ambiguity questions and answers,
- selected source classes (`repo`, `official_docs`, `web`, `mcp`, `alexandria`, `team`),
- trusted/private MCP policy,
- execution plan,
- evidence file list,
- verification checklist,
- final synthesis path,
- handoff recommendation.

First implementation can generate and inspect the plan without calling external deep-research models. Later implementations may connect to OpenAI Deep Research or Codex workflows, but the safety contract must already exist.

Security rules:

- Stage public-web research separately from private MCP research.
- Show trusted MCP servers and tool names before use.
- Log tool calls and model prompts used for evidence collection.
- Validate tool-call arguments with schemas.
- Do not render secrets in TUI or research reports by default.

## Command recipes and project-owned commands

The current command recipe system is a strong differentiator. The TUI should make it visible:

- `/commands` lists recipes with source, risk, steps, and dry-run availability.
- `/run <recipe>` should call the existing command planner and render the same plan as CLI JSON/human output.
- MCP recipe steps should show missing server/tool blockers rather than failing late.
- Project-owned recipes should appear alongside native commands in `/surface` but remain clearly separate.

## Persistence model

Current `.comx-agent/sessions` records should continue to exist and remain ignored runtime state. Expand session records over time with:

- rendered frames,
- command events,
- normalized router results,
- linked research artifacts,
- linked evidence reports,
- explicit exits/interrupts.

Do not persist raw secrets, full MCP env values, or unredacted headers.

## Implementation priorities for G004

1. Add a typed slash-command catalog and update completions/help to use it.
2. Add router/display results for read-only `/status`, `/commands`, `/mcp`, `/mcp tools <server>`, `/team`, `/ultragoal`, and `/research` plan creation.
3. Add TUI snapshot sections for MCP/command/session/runtime state without making the renderer parse raw data.
4. Add tests for command catalog, router results, redaction, and TUI JSON output.
5. Keep all mutation paths dry-run/preview-only unless a command already has explicit safe CLI behavior.

## Acceptance criteria

- `comx-agent tui --once --json` includes enough typed data to render status, command surface, MCP summary, and warnings.
- `/help` and completions are generated from one catalog.
- `/mcp` shows server rows, not only counts.
- `/mcp tools <server>` can be tested with a fake MCP client and surfaces errors clearly.
- `/research <objective>` writes a typed plan artifact and does not run external tools by default.
- Tests cover redaction of env/header/secret-like values.
- Ruff, Pyrefly, and focused tests pass.

## Open questions

1. Should research artifacts live under `.comx-agent/research/` or `.omx/reports/`? Default should be `.comx-agent/research/` for product-owned runtime state, while Ultragoal/team evidence can still mirror into `.omx/reports/`.
2. Should `/goal` call Codex native goal APIs directly, or only read our adapter-side goal surface? Start read-only and explicit.
3. Should `comx-agent` import current Codex project `.codex/config.toml` MCP servers? Prefer read-only visibility first; import must remain explicit.
