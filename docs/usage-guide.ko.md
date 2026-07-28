# comx-agent 스킬 및 사용 가이드

## 1. 목적

`comx-agent`는 Codex와 OMX를 대체하는 에이전트 프레임워크가 아니다.

다음 세 가지 사용 화면이 동일한 실행 코어를 공유하도록 만드는 로컬
Agent Development Environment(ADE)다.

- 사람이 사용하는 데스크톱 ADE
- 자동화나 진단에 사용하는 CLI
- Hermes 또는 신뢰된 컨트롤러가 사용하는 typed Python API

모든 실행 진실은 아래 9개 operation으로 관리된다.

```text
capabilities | plan | run | handoff | status
events | cancel | resume | artifacts
```

## 2. 빠른 시작

### 설치 및 상태 확인

```bash
uv sync
uv run comx-agent --help
uv run comx-agent capabilities
```

`capabilities`는 실제로 설치된 `codex`와 `omx` 바이너리 및 지원 가능한
operation을 검사한다. 바이너리가 있어도 현재 parser나 실행 환경이 맞지
않으면 `unsupported` 또는 ADE의 `observe-only` 상태로 표시될 수 있다.

### 데스크톱 ADE 실행

```bash
uv run comx-agent ade --cwd .
```

ADE를 닫는 것은 Run 취소가 아니다. 분리 실행된 Run은 native provider가
허용하는 범위에서 계속 실행되며, ADE를 다시 열면 durable Run record와
실제 process liveness를 다시 읽는다.

## 3. Codex 스킬 설치

저장소가 제공하는 스킬은 다음 경로에 있다.

```text
skills/omx-agent/
├── SKILL.md
└── agents/openai.yaml
```

저장소 Skill과 실제 Codex가 읽는 Skill을 다음 명령으로 동기화한다.

```bash
make install-agent-skill
make verify-agent-skill
```

이 명령은 `${CODEX_HOME:-$HOME/.codex}/skills/omx-agent/SKILL.md`만 갱신한다. `verify-agent-skill`은 저장소와 설치본의 drift를 검사한다. 설치 후 새 Codex 세션에서 다음처럼 호출한다.

```text
$omx-agent 현재 provider capability를 확인하고 ADE 사용 순서를 안내해줘
$omx-agent 이 변경을 Codex로 plan하고 검증 evidence까지 확인해줘
$omx-agent SOURCE_RUN_ID 결과를 OMX로 handoff해서 독립 검증해줘
```

이 스킬은 명령을 새로 만들지 않는다. 현재 저장소의 ADE, CLI, typed API
중 목적에 맞는 화면을 고르고 안전한 실행·검증 순서를 적용한다.

## 4. ADE 화면 사용법

### Projects & Workspaces

- **+ Project**: 기존 디렉터리를 Project로 등록한다.
- **+ Worktree**: 선택한 Git Project에 격리된 managed Worktree를 만든다.
- Sidebar: Project와 Workspace, branch, dirty, missing 상태를 보여준다.
- Finder/Editor/Terminal: 선택한 Workspace를 외부 macOS 앱에서 연다.

Project와 화면 선택 상태는 기본적으로 `~/.comx-agent/ade`에 저장된다.
이 값은 화면 편의를 위한 상태이며 Run의 실행 진실이 아니다.

상태 위치를 바꾸려면:

```bash
export COMX_AGENT_ADE_STATE_DIR=/safe/local/path/comx-ade-state
uv run comx-agent ade --cwd .
```

### New Run

1. **Recipe**를 선택한다.
2. Objective를 여러 줄로 작성한다.
3. **Review Plan**을 누른다.
4. provider, workspace, sandbox, mutation 여부, native argv, required
   Artifact를 확인한다.
5. 계획이 맞으면 **Start Run**을 누른다.

Plan 검토 전에는 Start Run이 비활성화된다. Plan과 Run은 같은
idempotency identity를 사용하므로 preview한 Run과 실제 실행 Run이
달라지지 않는다.

### Workspace Home

최근 Run의 다음 정보를 한눈에 보여준다.

- provider
- semantic status
- 실제 process liveness
- objective

Run을 선택하고 **Inspect Selected**를 누르거나 더블클릭하면 Run Detail로
이동한다.

### Attention

Attention은 단순 로그 목록이 아니라 조치가 필요한 evidence의 전역
목록이다.

- **Approval Required**: provider가 승인을 기다린다.
- **Input Required**: provider가 입력이나 답변을 기다린다.
- **Blocked / Failed**: Run, OMX Agent 또는 Task가 막혔거나 실패했다.
- **Stale**: 기록상 실행 중이지만 native process evidence가 없다.
- **Artifact Issue**: terminal Run의 필수 Artifact가 없거나 비어 있다.
- **Ready For Review**: 검증된 결과가 사람의 리뷰를 기다린다.

항목을 열면 일반 Run 화면이 아니라 해당 Activity event, Agent, Task,
Artifact 또는 Evidence tab으로 직접 이동한다.

### Run Detail

| Tab | 내용 |
| --- | --- |
| Overview | Run identity, status, liveness, provider session, failure |
| Agents | native OMX Team worker evidence 또는 명시적 unknown |
| Tasks | native OMX Task ownership과 상태 또는 명시적 unknown |
| Activity | 정규화된 lifecycle/provider/stdout/stderr event |
| Terminal | Workspace Terminal 또는 관찰된 OMX tmux attach |
| Diff | 현재 Workspace의 staged/unstaged/untracked diff |
| Artifacts | 검증된 result, logs, events, plan, declared Artifact |
| Evidence | semantic success와 provenance/verification 근거 |

Diff는 별도 baseline 증거가 없으면 “현재 Workspace diff”로 표시된다.
선택한 Run이 모든 변경을 만들었다고 추정하지 않는다.

### Run 제어

- **Cancel**: 기록된 native process에 bounded cancellation을 요청한다.
- **Resume**: native provider session ID가 있을 때만 재개한다.
- **Handoff**: 검증된 result를 다른 provider에 전달한다.
- **Attach Observed OMX tmux**: native evidence로 확인된 tmux session만
  연결한다.

Codex 또는 OMX가 session ID나 topology를 제공하지 않으면 ADE는 값을
추정하지 않고 unavailable/unknown으로 표시한다.

### Command Palette

macOS에서는 `Command-K`, 다른 환경에서는 `Control-K`로 연다.

Project 등록, Worktree 생성, Run 검사, terminal/tmux, cancel, resume,
handoff 등 화면에 있는 작업을 검색해서 실행할 수 있다. Command Palette는
단축 경로이며, 화면 버튼과 메뉴가 기본 사용 경로다.

## 5. ADE Recipe

| Recipe | Provider | Mutation | 용도 |
| --- | --- | --- | --- |
| Quick Review | Codex | 읽기 전용 | 저장소 분석, 리뷰, 근거 수집 |
| Implement Safely | Codex | workspace-write | 승인 가능한 작은 구현 |
| Implement and Verify | Codex | workspace-write | 구현 후 `verification.md` 증거 요구 |
| OMX Goal Execution | OMX | workspace-write | native OMX orchestration에 Goal 위임 |

Mutation Recipe를 선택했다는 사실만으로 무제한 변경이 허용되는 것은
아니다. Objective에 변경 범위와 검증 조건을 명시하고 Plan의 sandbox와
Artifact 계약을 반드시 확인한다.

## 6. Agent application surface

Agent는 GUI widget을 클릭하거나 화면 상태를 추측할 필요가 없다. 먼저 다음 명령으로 플랫폼 전체 context를 JSON으로 읽는다.

```bash
uv run comx-agent agent context
```

응답에는 다음이 포함된다.

- 등록된 Project와 Workspace catalog
- 현재 GUI 선택 상태(비권위적 참고값)
- 실제 Codex/OMX capability
- 사용 가능한 Recipe
- 각 Workspace의 branch, dirty, missing 상태
- 최근 Run과 evidence 기반 Attention

Project와 Worktree도 GUI와 동일한 service로 조작한다.

```bash
uv run comx-agent agent register-project /absolute/project/path
uv run comx-agent agent discover-worktrees PROJECT_ID
uv run comx-agent agent create-worktree PROJECT_ID agent/safe-change
uv run comx-agent agent adopt-workspace PROJECT_ID /related/worktree/path
uv run comx-agent agent inspect-workspace WORKSPACE_ID
```

`--state-root`를 사용하면 테스트나 격리된 controller가 별도 ADE catalog를 사용할 수 있다. 기본값은 GUI와 동일한 `COMX_AGENT_ADE_STATE_DIR` 또는 `~/.comx-agent/ade`다.

Agent의 권장 순서는 다음과 같다.

```text
agent context
-> Project/Workspace 준비
-> canonical Workspace path 확인
-> capabilities
-> plan
-> run
-> status/events/artifacts 및 Attention 재확인
```

Worktree 생성은 격리 공간만 만든다. mutation, commit, push 권한을 자동으로 부여하지 않는다.

### Agent 비동기 실행

Agent가 여러 Workspace를 운영하거나 호출 프로세스가 끝난 뒤에도 Run을 계속해야 한다면 GUI와 동일한 detached worker를 사용한다. 먼저 strict request JSON을 만든다.

```json
{
  "operation": "run",
  "request": {
    "controller_id": "trusted-agent",
    "provider": "codex",
    "objective": "선택한 Workspace를 수정하지 말고 검토해줘.",
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

`agent context`에도 detached operation 목록이 포함되므로 다른 Agent 프로세스가 같은 ADE state를 다시 읽고 관찰을 이어갈 수 있다. operation ID는 worker 추적 ID이고 Run ID와 다르다. operation 완료 후 result에 기록된 Run ID로 `status`, `events`, `artifacts`를 조회한다.

이 worker는 한 번에 하나의 기존 `HarnessTools` operation만 호출한다. 자체 스케줄러나 별도 lifecycle이 아니다.

## 7. Run lifecycle CLI 사용법

### 권장 순서

```text
capabilities → plan → run → status/events/artifacts
                         ↘ cancel/resume/handoff
```

### 읽기 전용 Codex Plan

```bash
uv run comx-agent plan \
  --provider codex \
  --cwd . \
  --idempotency-key review-20260728 \
  "저장소를 수정하지 말고 위험 요소와 가장 작은 개선안을 설명해줘."
```

`plan`은 provider를 실행하지 않는다.

### 읽기 전용 Codex Run

```bash
uv run comx-agent run \
  --provider codex \
  --cwd . \
  --idempotency-key review-20260728 \
  "저장소를 수정하지 말고 위험 요소와 가장 작은 개선안을 설명해줘."
```

같은 idempotency key와 같은 요청을 재시도하면 uncontrolled duplicate Run을
만들지 않는다. 같은 key에 다른 요청을 넣으면 충돌로 거절된다.

### 명시적 변경 Run

```bash
uv run comx-agent run \
  --provider codex \
  --cwd . \
  --mutation \
  --sandbox workspace-write \
  --approval on-request \
  --expected-artifact verification.md \
  "요청된 변경만 구현하고 verification.md에 검증 결과를 기록해줘."
```

`--mutation` 없이 write sandbox를 요청하거나, mutation을 허용하면서
read-only sandbox를 사용하는 모순된 요청은 contract validation에서
거절된다.

### OMX Run

```bash
uv run comx-agent run \
  --provider omx \
  --cwd . \
  --read-only \
  --sandbox read-only \
  "GOAL.md를 읽고 현재 구현을 독립적으로 검토해줘."
```

Team, Ralph, UltraGoal, mission, capability lock은 OMX가 소유한다.
`comx-agent`는 이를 Python workflow로 복제하지 않는다.

### 상태와 증거 확인

```bash
uv run comx-agent status RUN_ID --cwd .
uv run comx-agent events RUN_ID --cwd .
uv run comx-agent artifacts RUN_ID --cwd .
```

`status`는 semantic status와 process liveness를 구분한다. exit code 0만으로
성공하지 않으며 필수 result, plan, declared Artifact가 실제로 존재하고
비어 있지 않아야 한다.

### 취소와 재개

```bash
uv run comx-agent cancel RUN_ID --cwd .

uv run comx-agent resume RUN_ID \
  --cwd . \
  --idempotency-key resume-RUN_ID-01 \
  --objective "이전 근거를 유지하면서 남은 검증을 완료해줘."
```

Resume은 원본 Run에 native provider session ID가 없으면 명시적으로
실패한다.

### Cross-provider handoff

```bash
uv run comx-agent handoff SOURCE_RUN_ID \
  --target-provider omx \
  --cwd . \
  --idempotency-key handoff-SOURCE_RUN_ID-omx-01 \
  "Codex 결과의 주장과 Artifact를 독립 검증해줘."
```

Handoff는 source Run ID, provider, Artifact SHA-256과 검증된 본문을 target
provider에 전달한다. 같은 provider로의 handoff는 native composition을
사용해야 하므로 거절된다.

## 8. Python API

```python
from comx_harness import (
    AdeAgentTools,
    AgentContextRequest,
    ExecutionRequest,
    HarnessTools,
    RunReference,
)

platform = AdeAgentTools()
context = platform.context(AgentContextRequest())
workspace = context.catalog.workspaces[0].root_path

tools = HarnessTools()
record = tools.run(
    ExecutionRequest(
        controller_id="trusted-controller",
        provider="codex",
        objective="Read-only verification of the current implementation.",
        workspace=workspace,
        idempotency_key="trusted-review-01",
    )
)
state = tools.status(
    RunReference(workspace=workspace, run_id=record.run_id)
)
```

`AdeAgentTools`는 Project/Workspace/Worktree/Attention application facade이고, `HarnessTools`는 얇은 Run lifecycle facade다. lifecycle logic은
`HarnessService`가 소유하며 CLI, ADE, Hermes가 별도 Run truth를 만들면
안 된다.

## 9. 저장 위치

Workspace별 실행 기록:

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
└── idempotency/
```

ADE 화면 상태:

```text
~/.comx-agent/ade/
├── catalog.json
├── view-context.json
└── operations/<operation-id>/
```

ADE state는 Project/Workspace/선택 tab 같은 화면 상태와 detached operation
metadata만 가진다. authoritative Run record는 항상 Workspace의
`.comx-agent/v2`에 있다.

## 10. 문제 해결

### ADE가 Tcl/Tk 오류로 열리지 않음

macOS launcher는 현재 Python의 Tk를 먼저 검사하고, 필요하면 호환되는
Python 3.13 framework interpreter로 전환하면서 설치된 `comx_harness`
경로를 유지한다.

```bash
uv run comx-agent ade --cwd .
```

여전히 실패하면 출력된 “usable Tk support” 진단과 설치된 Python 3.13
framework/Tk 상태를 확인한다.

### provider가 missing 또는 observe-only

```bash
uv run comx-agent capabilities
which codex
which omx
```

현재 소유권이 있는 OMX/tmux 세션 안에서는 새 OMX 실행이 충돌할 수 있다.
이 경우 저장된 Run 관찰은 가능하지만 새 실행은 정상 shell에서 시작해야
할 수 있다.

### Run이 성공하지 않음

```bash
uv run comx-agent status RUN_ID --cwd .
uv run comx-agent events RUN_ID --cwd .
uv run comx-agent artifacts RUN_ID --cwd .
```

`failure.code`, `failure.message`, `stderr.log`, required Artifact의
`exists`, `size_bytes`, `sha256`을 함께 확인한다.

외부 MCP의 OAuth가 만료된 경우 provider 로그에 인증 실패가 남을 수 있다.
인증을 복구한 뒤 새 Run 또는 지원되는 resume을 사용한다. 기존 Run을
성공으로 가장하지 않는다.

### Resume이 거절됨

원본 Run의 `provider_session_id`가 없거나 provider가 native resume
contract를 지원하지 않는 경우다. 새 Run이 필요한지는 controller가
결정해야 하며 harness가 가짜 resume을 만들지 않는다.

## 11. 개발자 검증

```bash
make ruff
make pyrefly
make test
make ci
make native-test
```

`make ci`는 deterministic test와 wheel build를 포함한다.
`make native-test`는 설치된 Codex/OMX parser contract를 확인한다.

커밋과 push는 `comx-agent`가 자동으로 수행하지 않는다.
