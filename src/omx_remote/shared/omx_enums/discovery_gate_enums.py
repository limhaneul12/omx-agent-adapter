from enum import StrEnum


class DiscoveryGateProfile(StrEnum):
    """Depth profiles for discovery-gate clarification work."""

    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class DiscoveryGateVerdict(StrEnum):
    """Allowed discovery-gate routing verdicts."""

    READY_FOR_RESEARCH = "ready-for-research"
    READY_FOR_PRD = "ready-for-prd"
    READY_FOR_IMPLEMENTATION_KICKOFF = "ready-for-implementation-kickoff"
    READY_FOR_COMPANY_RUN = "ready-for-company-run"
    RESEARCH_FIRST = "research-first"
    ASK_USER = "ask-user"
    RUN_DEEP_INTERVIEW = "run-deep-interview"
    REROUTE_SMALL_TASK = "reroute-small-task"
    NO_BUILD = "no-build"
    BLOCKED = "blocked"
    SKIPPED_CLEAR_ENOUGH = "skipped-clear-enough"


class DiscoveryGateTaskSize(StrEnum):
    """Task-size labels used by discovery-gate decision packets."""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    ROADMAP = "roadmap"


class DiscoveryGateCompanyRunSuitability(StrEnum):
    """Company-run suitability labels produced before macro orchestration."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    BLOCKED = "blocked"


class DiscoveryGateResearchNeed(StrEnum):
    """Research need labels for routing discovery output."""

    NOT_NEEDED = "not-needed"
    RESEARCH_FIRST = "research-first"
    RESEARCH_MORE = "research-more"


class DiscoveryGateDeepInterviewMode(StrEnum):
    """Concrete relationship between discovery-gate and OMX deep-interview."""

    SKIP = "skip"
    HANDOFF = "handoff"
    MANAGED_INTERVIEW = "managed-interview"
    RESUME_IMPORT = "resume-import"


class DiscoveryGateStatus(StrEnum):
    """Status values emitted by discovery-gate result packets."""

    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    REQUIRES_AGENT_ACTION = "requires_agent_action"
    FAILED = "failed"


class DiscoveryGateDelegationLevel(StrEnum):
    """Decision authority captured by a discovery-gate run."""

    ASK_USER_FOR_MATERIAL_DECISIONS = "ask-user-for-material-decisions"
    FULL_DELEGATE_TO_ORCHESTRATOR = "full-delegate-to-orchestrator"
    UNSPECIFIED = "unspecified"
