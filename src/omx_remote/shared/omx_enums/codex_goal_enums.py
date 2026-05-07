from enum import StrEnum


class CodexGoalExecutionShape(StrEnum):
    """Execution modes supported by the adapter-owned Codex Goal launch surface."""

    GOAL_ONLY = "goal_only"
    RALPH_PIPELINE = "ralph_pipeline"


class CodexGoalReviewPolicy(StrEnum):
    """Review policies that decide whether Ralph PRD handoff pauses for approval."""

    REVIEW_REQUIRED = "review_required"
    CONTINUE_AUTOMATICALLY = "continue_automatically"


class CodexGoalMirrorSource(StrEnum):
    """Sources that can produce adapter-owned Codex Goal mirror state."""

    CODEX_GOAL = "codex_goal"


class CodexGoalHandoffState(StrEnum):
    """Adapter-visible progress markers for Goal-to-Ralph handoff state."""

    GOAL_ONLY = "goal_only"
    AWAITING_RALPH = "awaiting_ralph"
    RALPH_STARTED = "ralph_started"
    UNKNOWN = "unknown"


class CodexGoalTrackingState(StrEnum):
    """Lifecycle states tracked by the adapter for a native Codex Goal session."""

    STARTING = "starting"
    ACTIVE = "active"
    ENDED = "ended"
    UNKNOWN = "unknown"


class CodexGoalSpawnStatus(StrEnum):
    """Native Codex Goal process spawn outcomes observed by the adapter."""

    STARTED = "started"
    FAILED = "failed"


class CodexGoalStatus(StrEnum):
    """Goal snapshot status values consumed by delegation selection."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETE = "complete"
    CLEARED = "cleared"
    UNKNOWN = "unknown"


class CodexGoalSource(StrEnum):
    """Goal snapshot producers visible to the supervisor layer."""

    CODEX_GOAL = "codex_goal"
    ADAPTER_SUPERVISOR = "adapter_supervisor"


class GoalDelegationTarget(StrEnum):
    """Delegation targets selected from a Codex Goal snapshot and operator state."""

    GOAL_ONLY = "goal_only"
    RALPH_PIPELINE = "ralph_pipeline"
    OBSERVE_ONLY = "observe_only"
    PLAIN_EXEC = "plain_exec"


class GoalDelegationDispatchStatus(StrEnum):
    """Dispatch outcomes for a selected Goal delegation target."""

    NOT_APPLICABLE = "not_applicable"
    BLOCKED = "blocked"
    DISPATCHED = "dispatched"


class GoalDelegationDispatchAction(StrEnum):
    """Concrete runtime actions performed by Goal delegation dispatch."""

    NONE = "none"
    RALPH_LAUNCH = "ralph_launch"
    RALPH_RESUME = "ralph_resume"
    TEAM_LAUNCH = "team_launch"


class GoalRalphPrdReviewMode(StrEnum):
    """Review gates available before Goal dispatches a typed PRD into Ralph."""

    LLM_PROMPT = "llm_prompt"
    AUTO_APPROVE = "auto_approve"


class CodexGoalLifecycleAction(StrEnum):
    """Goal lifecycle actions selected after Ralph post-Team review."""

    CLOSE_GOAL = "close_goal"
    PREPARE_FOLLOW_UP_WAVE = "prepare_follow_up_wave"
    WAIT_FOR_HUMAN_REVIEW = "wait_for_human_review"


class CodexGoalLifecycleTarget(StrEnum):
    """Next control-surface targets for Goal lifecycle decisions."""

    GOAL_CLOSE = "goal_close"
    RALPH_FOLLOW_UP = "ralph_follow_up"
    HUMAN_REVIEW = "human_review"


class CodexGoalLifecycleRestoreTarget(StrEnum):
    """Resume targets derived from durable Goal lifecycle artifacts."""

    TEAM_ADMIN_AGGREGATION = "team_admin_aggregation"
    RALPH_POST_TEAM_REVIEW = "ralph_post_team_review"
    GOAL_LIFECYCLE_DECISION = "goal_lifecycle_decision"
    GOAL_CLOSE = "goal_close"
    RALPH_FOLLOW_UP = "ralph_follow_up"
    HUMAN_REVIEW = "human_review"


class CodexGoalOperatingStage(StrEnum):
    """Agent-facing Goal/OMX operating stages derived from lifecycle state."""

    TEAM_ADMIN_AGGREGATION_PENDING = "team_admin_aggregation_pending"
    RALPH_POST_TEAM_REVIEW_PENDING = "ralph_post_team_review_pending"
    GOAL_LIFECYCLE_DECISION_PENDING = "goal_lifecycle_decision_pending"
    GOAL_CLOSE_READY = "goal_close_ready"
    RALPH_FOLLOW_UP_READY = "ralph_follow_up_ready"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class CodexGoalOperatingAction(StrEnum):
    """Next actions an agent can take while operating OMX through Goal lifecycle state."""

    COLLECT_TEAM_ADMIN_AGGREGATION = "collect_team_admin_aggregation"
    RUN_RALPH_POST_TEAM_REVIEW = "run_ralph_post_team_review"
    BUILD_GOAL_LIFECYCLE_DECISION = "build_goal_lifecycle_decision"
    CLOSE_GOAL = "close_goal"
    PREPARE_RALPH_FOLLOW_UP = "prepare_ralph_follow_up"
    WAIT_FOR_HUMAN_REVIEW = "wait_for_human_review"


class CodexGoalOperatingEvidenceSource(StrEnum):
    """Evidence sources agents should inspect before mutating OMX or Goal state."""

    GOAL_LIFECYCLE_ARTIFACT = "goal_lifecycle_artifact"
    OMX_TEAM_API_LIST_TASKS = "omx_team_api_list_tasks"
    OMX_TEAM_API_READ_EVENTS = "omx_team_api_read_events"
    OMX_TEAM_API_READ_WORKER_STATUS = "omx_team_api_read_worker_status"
    TEAM_ADMIN_AGGREGATION_REPORT = "team_admin_aggregation_report"
    RALPH_POST_TEAM_REVIEW_RESULT = "ralph_post_team_review_result"
    GOAL_LIFECYCLE_DECISION = "goal_lifecycle_decision"
