from enum import StrEnum


class CommandSource(StrEnum):
    """Sources that can provide project-owned command recipes."""

    BUILTIN = "builtin"
    REPO = "repo"
    ONE_OFF = "one_off"


class CommandRisk(StrEnum):
    """Command risk classes used for dry-run planning."""

    READ_ONLY = "read_only"
    WRITES_FILES = "writes_files"
    LAUNCHES_RUNTIME = "launches_runtime"
    LONG_RUNNING = "long_running"
    EXTERNAL_NETWORK = "external_network"


class CommandStepCommand(StrEnum):
    """Supported composed-command step kinds."""

    CODEX_EXEC = "codex_exec"
    OMX_EXEC = "omx_exec"
    OMX_ULTRAGOAL = "omx_ultragoal"
    OMX_TEAM = "omx_team"
    OMX_RALPH = "omx_ralph"
    MCP_TOOL = "mcp_tool"
    LOCAL = "local"
    PROMPT_ONLY = "prompt_only"


class CodexSandboxMode(StrEnum):
    """Supported Codex sandbox modes for composed-command previews."""

    READ_ONLY = "read-only"
    WORKSPACE_WRITE = "workspace-write"
    DANGER_FULL_ACCESS = "danger-full-access"


class CommandRecipeProvider(StrEnum):
    """Shorthand command recipe provider values accepted from repo config."""

    CODEX = "codex"
    OMX = "omx"
    LOCAL = "local"
    MCP = "mcp"


class CommandRecipeMode(StrEnum):
    """Shorthand command recipe mode values accepted from repo config."""

    EXEC = "exec"
    ULTRAGOAL = "ultragoal"
    TEAM = "team"
    RALPH = "ralph"
    LOCAL = "local"
    MCP_TOOL = "mcp_tool"
    TOOL = "tool"
    PROMPT = "prompt"


class CommandAutonomyMode(StrEnum):
    """Supported autonomy modes for actual command execution."""

    AGENT = "agent"


class CommandAutonomyDecisionKind(StrEnum):
    """Agent policy decisions before or during execution."""

    ALLOW = "allow"
    BLOCK = "block"
    RETRY = "retry"
    RECOVER = "recover"
    DEFER = "defer"


class CommandActualRunStatus(StrEnum):
    """Final status for an actual composed-command run."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    REQUIRES_AGENT_ACTION = "requires_agent_action"


class CommandStepExecutionStatus(StrEnum):
    """Execution status for one planned command step."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    RECOVERED = "recovered"
    REQUIRES_AGENT_ACTION = "requires_agent_action"


class CommandFailureKind(StrEnum):
    """Normalized failure classes for retry and recovery decisions."""

    TRANSIENT_NETWORK = "transient_network"
    TIMEOUT = "timeout"
    MISSING_ARTIFACT = "missing_artifact"
    LINT_FAILURE = "lint_failure"
    TEST_FAILURE = "test_failure"
    RUNTIME_CONFLICT = "runtime_conflict"
    DIRTY_WORKTREE = "dirty_worktree"
    MISSING_TOOL = "missing_tool"
    INVALID_COMMAND = "invalid_command"
    PERMISSION_OR_POLICY_BLOCK = "permission_or_policy_block"
    UNKNOWN_FAILURE = "unknown_failure"


class CommandRecoveryAction(StrEnum):
    """Recovery actions a failed step can take before final failure."""

    NONE = "none"
    RETRY_STEP = "retry_step"
    WRITE_HANDOFF = "write_handoff"
    MATERIALIZE_ARTIFACTS = "materialize_artifacts"
    FINAL_FAIL = "final_fail"
