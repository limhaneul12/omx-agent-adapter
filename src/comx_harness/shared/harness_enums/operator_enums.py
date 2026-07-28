from enum import StrEnum


class RecipeId(StrEnum):
    QUICK_REVIEW = "quick-review"
    IMPLEMENT_SAFELY = "implement-safely"
    IMPLEMENT_AND_VERIFY = "implement-and-verify"
    OMX_GOAL_EXECUTION = "omx-goal-execution"


class AttentionKind(StrEnum):
    APPROVAL_REQUIRED = "approval_required"
    INPUT_REQUIRED = "input_required"
    BLOCKED = "blocked"
    FAILED = "failed"
    STALE = "stale"
    ARTIFACT_ISSUE = "artifact_issue"
    READY_FOR_REVIEW = "ready_for_review"


class AttentionEntityKind(StrEnum):
    RUN = "run"
    EVENT = "event"
    AGENT = "agent"
    TASK = "task"
    ARTIFACT = "artifact"


class RunDetailTab(StrEnum):
    OVERVIEW = "Overview"
    AGENTS = "Agents"
    TASKS = "Tasks"
    ACTIVITY = "Activity"
    TERMINAL = "Terminal"
    DIFF = "Diff"
    ARTIFACTS = "Artifacts"
    EVIDENCE = "Evidence"


class AgentStatus(StrEnum):
    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"
    DRAINING = "draining"
    UNKNOWN = "unknown"
