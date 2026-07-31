# comx-agent

`comx-agent` is a local, single-user **Agent Harness Workbench** backed by an **Agent Execution Control Plane**. A human can use the GUI or CLI, while Hermes or another trusted Agent can use the typed CLI or application surface. All clients submit work to the same durable Runtime.

The project does not replace native Codex reasoning or OMX orchestration. Its normal public contract is a typed `Mission`; the platform compiles that Mission into inspectable bounded Strategy IR and reuses the exact-nine Run lifecycle for execution, state, artifacts, cancellation, resume, and cross-provider handoff.

`GOAL.md` is the product source of truth.

## Public surface

```text
capabilities   Discover Codex and OMX support.
plan           Preview the exact native execution contract.
run            Execute one task on one provider.
handoff        Pass a verified artifact to the other provider.
status         Read semantic state and process liveness.
events         Read normalized lifecycle and provider events.
cancel         Request bounded native-process cancellation.
resume         Resume when a native provider session id exists.
artifacts      Read result, logs, events, plan, and declared evidence.
```

The nine operations are the Run lifecycle core. Mission and Strategy coordinate those operations; neither creates a second provider lifecycle. The desktop ADE, CLI, and typed Agent surfaces share the same Project, Workspace, Worktree, Attention, Strategy, Run, event, artifact, and evidence state.

## Installation

```bash
uv sync
uv run comx-agent --help
```

## Skill and usage / 스킬 및 사용법

The repository ships one Codex skill for operating the current ADE and typed
execution core:

```text
skills/omx-agent/SKILL.md
```

Install or update it through the repository-owned target:

```bash
make install-agent-skill
make verify-agent-skill
```

The installer updates only `${CODEX_HOME:-$HOME/.codex}/skills/omx-agent/SKILL.md`. Invoke the installed skill with:

```text
$omx-agent
```

Example prompts:

```text
$omx-agent 이 저장소를 ADE로 읽기 전용 검토해줘
$omx-agent Codex 결과를 OMX로 검증 handoff 하는 안전한 절차를 실행해줘
$omx-agent 이 Run의 status, events, artifacts를 확인하고 실패 원인을 설명해줘
```

The skill does not add another workflow engine or lifecycle operation. It
selects and applies the existing ADE, CLI, or typed Python surface.

For the complete Korean operator guide, including Recipes, Attention, Run
Detail tabs, CLI examples, storage, safety, and troubleshooting, see
[`docs/usage-guide.ko.md`](docs/usage-guide.ko.md).

## Agent application surface

Agents do not need to automate the desktop GUI. Start with one machine-readable platform snapshot:

```bash
uv run comx-agent agent context
```

The returned strict JSON includes registered Projects and Workspaces, live Git state, provider capabilities, Recipes, recent Runs, and evidence-based Attention. Application actions use the same services as the GUI:

```bash
uv run comx-agent agent register-project /absolute/project/path
uv run comx-agent agent discover-worktrees PROJECT_ID
uv run comx-agent agent create-worktree PROJECT_ID agent/isolated-change
uv run comx-agent agent inspect-workspace WORKSPACE_ID
```

The Python equivalent is `AdeAgentTools`. Use it for Project/Workspace/Worktree context, then use `HarnessTools` for the exact-nine Run lifecycle. Worktree creation never implies commit or push permission.

For Orca-like non-blocking operation, serialize one strict detached request and start it through the same worker used by the desktop ADE:

```json
{
  "operation": "run",
  "request": {
    "controller_id": "trusted-agent",
    "provider": "codex",
    "objective": "Inspect the selected Workspace without modifying files.",
    "workspace": "/absolute/workspace/path",
    "idempotency_key": "agent-review-01"
  }
}
```

```bash
uv run comx-agent agent start-operation operation.json
uv run comx-agent agent operation OPERATION_ID
uv run comx-agent agent operations
```

`agent context` also includes detached operation records, so another agent process can reopen the same ADE state and continue observation. The per-operation worker still calls exactly one existing `HarnessTools` operation; it is not a scheduler or a second runtime.

### Mission-first execution

For normal human or Agent use, submit one strict Mission instead of manually authoring Strategy stages:

```json
{
  "schema_version": "mission-request.v1",
  "mission_id": "repository-review-001",
  "controller_id": "human-cli",
  "objective": "Inspect the repository without modifying it.",
  "workspace": "/absolute/workspace/path",
  "execution_profile": "codex-native"
}
```

Complete strict templates are available under [`examples/missions/`](examples/missions/README.md). Copy one, replace `mission_id` with a unique value, and set the canonical Workspace path before execution.

```bash
uv run comx-agent agent capabilities
uv run comx-agent agent plan-mission mission.json
uv run comx-agent agent validate-mission mission.json
uv run comx-agent agent execute-mission mission.json
uv run comx-agent agent mission-status /absolute/workspace MISSION_ID
uv run comx-agent agent mission-events /absolute/workspace MISSION_ID
uv run comx-agent agent mission-artifacts /absolute/workspace MISSION_ID
```

Mission execution is detached by default. Use `--foreground` only for tests or bounded operator workflows. Reusing a `mission_id` with a different request is rejected; re-observe the existing Mission instead. The initial explicit profiles are:

```text
codex-native
omx-native
codex-then-omx-review
```

There is deliberately no `auto` profile yet. The platform will consider evidence-driven profile recommendations only after real Mission history can compare completion, verification, elapsed time, retries, regressions, valid review blockers, and human intervention.

Read-only is the default. Mutation requires both `constraints.mutation_allowed=true` and an explicit writable sandbox. The initial Mission contract rejects arbitrary shell fields and denies commit and push.

The cross-provider profile compiles deterministically to Codex execution, OMX verified handoff review, a `blocker-report.v1` validator, conditional Codex resume only when verified blockers exist, and a final evidence gate. It requires a writable sandbox because the reviewer must write the harness-owned blocker artifact; use an isolated Git worktree for the first live run. See [`docs/architecture/mission-runtime.md`](docs/architecture/mission-runtime.md).

`agent capabilities` separates installation, parser compatibility, authentication knowledge, and live execution readiness. A local ChatGPT login or accepted `--help` contract is not live Mission proof. Until a native Mission succeeds end to end, readiness remains `conditional` and the limitation must be reported rather than inferred away.

### Advanced/debug Strategy IR

A trusted expert caller may still submit strict Strategy IR directly. This is retained for debugging, deterministic Runtime tests, replay, and advanced integrations rather than as the normal product surface. The first schema supports `native_run`, `native_resume`, `handoff`, `validator`, and `finish` nodes over one Workspace. It supports a sequential order plus three bounded conditions: all dependencies succeeded, any dependency succeeded, or any dependency failed. There is no arbitrary shell node or general graph engine.

```bash
uv run comx-agent agent capabilities
uv run comx-agent agent validate-strategy strategy.json
uv run comx-agent agent execute-strategy strategy.json
uv run comx-agent agent strategy-launch /absolute/workspace STRATEGY_ID
uv run comx-agent agent strategy-status /absolute/workspace STRATEGY_ID
uv run comx-agent agent strategy-events /absolute/workspace STRATEGY_ID
uv run comx-agent agent strategy-artifacts /absolute/workspace STRATEGY_ID
```

Execution is detached by default. `--foreground` is available for tests and bounded operator workflows. A Strategy worker calls the existing `run`, `resume`, `handoff`, `status`, and `artifacts` contracts. It never owns provider authentication and never asks for an OpenAI API key.

Capability discovery distinguishes binary installation, authentication knowledge, execution readiness, and unavailability. `supported`, `conditional`, `unsupported`, and `unknown` are separate states. Codex authentication is probed through the local `codex login status` command without reading or storing a token. OMX authentication remains conditional on that local Codex login until an OMX native execution succeeds. Parser compatibility and diagnostic commands alone are not reported as live execution proof.

Evidence-based completion uses native exit status, normalized Run status, required artifact existence, non-zero size, and SHA-256 digest. A blocker-controlled resume requires a verified `blocker-report.v1` JSON artifact; model prose is not parsed to invent a blocker count.

## Human ADE

Open the native local desktop application in the current project:

```bash
uv run comx-agent ade --cwd .
```

The ADE remains part of the product as a thin Human Control Plane. It does not own provider execution or separate Runtime truth. In the Mission tab, enter the objective, select an explicit profile, confirm mutation, sandbox, approval, and timeout, preview `MissionService.plan()` output, and then submit the detached Mission. Continue observation through the authoritative durable Strategy and Run state rather than a GUI-only copy.

The ADE uses Python's standard-library desktop toolkit, so the wheel adds no
second JavaScript runtime or application server. It provides:

- persistent Project, Workspace, and Git Worktree navigation,
- visible branch, dirty, missing, Run, liveness, and Attention state,
- multiline objective editing and discoverable Recipe selection,
- exact idempotent Plan preview before execution,
- Mission plan preview and detached Mission submission through the shared service,
- detached Run, resume, and handoff workers that survive ADE closure,
- read-only Strategy and Stage observation from Workspace Runtime state,
- fast switching between recent Runs,
- stable Overview, Agents, Tasks, Activity, Terminal, Diff, Artifacts, and
  Evidence tabs,
- read-only OMX Team worker and Task observation where native evidence exists,
- verified bounded Artifact content,
- external Finder, editor, and Terminal actions on macOS,
- a searchable command palette,
- bounded cancel and supported resume,
- verified Codex-to-OMX or OMX-to-Codex handoff,
- and restoration of selected Project, Workspace, Run, detail tab, reviewed
  state, and window geometry.

Project and view state live under `~/.comx-agent/ade` by default and can be
relocated with `COMX_AGENT_ADE_STATE_DIR`. This state is non-authoritative: Run
truth remains in each Workspace's `.comx-agent/v2` store.

On macOS, the launcher checks whether the active Python environment has a
working Tk runtime. If a `uv`-managed interpreter lacks its Tcl/Tk resources, it
uses a compatible Python 3.13 framework interpreter for the desktop runtime
while retaining the invoking installation's `comx_harness` and dependencies.
If no compatible Tk runtime exists, launch fails with an explicit diagnostic
instead of a Tcl stack trace.

Run, resume, and handoff launch one detached per-operation worker. The worker
calls the same `HarnessTools` and `HarnessService` operations as the CLI and
Hermes; it is not a daemon, scheduler, provider, or second lifecycle core.

The ADE can close while a worker is active. Reopening the same Workspace
reconciles durable Run records with actual process liveness. Closing the ADE and
cancelling a Run are separate actions.

For OMX Team Runs, observation uses only installed native JSON interfaces:
`omx team status`, `read-config`, `list-tasks`, `get-summary`, and
`read-monitor-snapshot`. It shows only reported workers, roles, ownership,
heartbeat, Worktree, blocked/failed Task, and Attention evidence.

Codex nested subagent topology remains unknown unless Codex exposes equivalent
structured native evidence. The ADE does not infer it from model text. OMX Team
observation is read-only: the ADE does not create workers, assign Tasks, resize
teams, route messages, or shut down teams.

The ADE does not own the Strategy Runtime or a workflow engine, embedded source editor, browser
automation environment, GitHub client, long-term memory, or provider
orchestration.

The shipped wheel's only Python runtime package is `comx_harness`. The previous
workflow-heavy `omx_remote` implementation and its compatibility entrypoints are
not part of the distribution.

## Capability discovery

```bash
uv run comx-agent capabilities
```

Discovery checks the actual installed `codex` and `omx` binaries and probes whether each binary accepts the harness direct-run and resume argument contracts. A binary may be present while execution capabilities are reported unsupported when its native parser is incompatible. Unsupported operations are reported explicitly rather than simulated.

## Plan a run

```bash
uv run comx-agent plan \
  --provider codex \
  --cwd . \
  "Inspect the current repository and explain the smallest safe change."
```

A plan contains the resolved provider, native argv, workspace, controller, execution options, artifact paths, and cancel/resume support. Planning does not launch the provider.

## Direct Codex execution

Read-only is the default:

```bash
uv run comx-agent run \
  --provider codex \
  --cwd . \
  "Review the repository and produce a concise evidence-backed report."
```

Mutation must be explicit:

```bash
uv run comx-agent run \
  --provider codex \
  --cwd . \
  --mutation \
  --sandbox workspace-write \
  --expected-artifact CHANGELOG.md \
  "Implement the requested change and verify it."
```

## Direct OMX execution

```bash
uv run comx-agent run \
  --provider omx \
  --cwd . \
  "Use the native OMX environment to complete the objective."
```

The harness uses `omx exec`; native OMX features such as Team, Ralph, UltraGoal, missions, and capability locks remain native provider features. They are not recreated as adapter workflows.

## Cross-runtime handoff

First create a verified source run, then pass its result to the other provider:

```bash
uv run comx-agent handoff RUN_ID \
  --target-provider omx \
  --cwd . \
  "Validate the Codex result and continue only from supported evidence."
```

The receiving prompt contains the origin run id, source provider, artifact digest, and verified artifact body. Same-provider composition is rejected because it should use native Codex or native OMX behavior.

## Observe and control

```bash
uv run comx-agent status RUN_ID --cwd .
uv run comx-agent events RUN_ID --cwd .
uv run comx-agent artifacts RUN_ID --cwd .
uv run comx-agent cancel RUN_ID --cwd .
uv run comx-agent resume RUN_ID --cwd . --objective "Continue and finish."
```

Resume fails explicitly when native JSONL output did not expose a provider session id.

## Run storage

Each workspace owns a local single-user store:

```text
.comx-agent/v2/
├── runs/<run-id>/
│   ├── plan.json
│   ├── run.json
│   ├── result.md
│   ├── stdout.log
│   ├── stderr.log
│   └── events.jsonl
├── handoffs/<handoff-id>.json
├── strategies/<strategy-id>/
│   ├── strategy.json
│   ├── events.jsonl
│   ├── request.json
│   ├── launch.json
│   ├── result.json
│   ├── worker.stdout.log
│   └── worker.stderr.log
└── idempotency/
    ├── <sha256>.json
    └── locks/<sha256>.lock
```

A provider process exiting with code zero is not enough for success. `result.md`, `plan.json`, and every declared required artifact must exist, be non-empty, and have a digest before the run is reported as `succeeded`. Strategy state references those verified Run artifacts rather than copying provider claims into a second truth store.

## Python and Hermes integration

```python
from comx_harness import ExecutionRequest, HarnessTools, RunReference

tools = HarnessTools()
record = tools.run(
    ExecutionRequest(
        controller_id="hermes-builder",
        provider="codex",
        objective="Verify the design and implement the smallest valid change.",
        workspace=".",
    )
)
state = tools.status(RunReference(workspace=".", run_id=record.run_id))
```

`HarnessTools` exposes the same nine typed operations used by the CLI: `capabilities`, `plan`, `run`, `handoff`, `status`, `events`, `cancel`, `resume`, and `artifacts`. It contains no lifecycle logic and delegates every operation to `HarnessService`.

Hermes owns objective interpretation and runtime choice. Codex or OMX owns native reasoning. The harness owns invocation, lifecycle, evidence, and provider-to-provider handoff.

## Verification

```bash
make ruff
make pyrefly
make test
make ci
```

When installed locally, Codex and OMX parser-contract tests validate the generated direct-run and resume argv without starting a model request. Those tests skip honestly when a native binary is absent. Fake-provider end-to-end tests validate lifecycle, evidence, concurrency, cancellation, resume, controller parity, and bidirectional handoff.

A real model-backed smoke run requires the surrounding execution environment to authorize networked native execution. Parser compatibility, capability discovery, planning, packaging, and local lifecycle tests do not claim that this external authorization step has completed.

No commit or push is performed by the harness itself.
