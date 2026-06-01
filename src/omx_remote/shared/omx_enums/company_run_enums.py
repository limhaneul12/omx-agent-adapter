from enum import StrEnum


class CompanyRunRoleGroup(StrEnum):
    """Company-run organization groups with runtime ownership meaning."""

    CEO = "ceo"
    RESEARCH = "research"
    PRODUCT = "product"
    EXECUTIVE = "executive"
    TEAM = "team"
    REVIEW = "review"
    ALEXANDRIA = "alexandria"


class CompanyRunPhase(StrEnum):
    """Ordered phases for the real company-run execution engine."""

    MEMORY_RECALL = "memory_recall"
    DISCOVERY_GATE = "discovery_gate"
    ROUTE_NEXT = "route_next"
    RESEARCH_BRIEF_LOOP = "research_brief_loop"
    RESEARCH_COMPLETION_VOTE = "research_completion_vote"
    PROCEED_VOTE = "proceed_vote"
    IDEA_TO_PRD = "idea_to_prd"
    EXECUTIVE_READINESS_GATE = "executive_readiness_gate"
    IMPLEMENTATION_KICKOFF = "implementation_kickoff"
    TEAM_BOOTSTRAP = "team_bootstrap"
    TEAM_SYNC_LOOP = "team_sync_loop"
    INTEGRATION_PLAN_LOOP = "integration_plan_loop"
    REVIEW_GATE_LOOP = "review_gate_loop"
    RELEASE_READINESS = "release_readiness"
    MEMORY_CLOSEOUT = "memory_closeout"


class CompanyRunPhaseStatus(StrEnum):
    """Status values for company-run phase ledger entries."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    REQUIRES_AGENT_ACTION = "requires_agent_action"


class CompanyRunVoteChoice(StrEnum):
    """Vote choices used by research, proceed, readiness, review, and release gates."""

    RESEARCH_COMPLETE = "research-complete"
    RESEARCH_MORE = "research-more"
    PROCEED_TO_PRD = "proceed-to-prd"
    READY_FOR_IMPLEMENTATION = "ready-for-implementation-kickoff"
    APPROVE = "approve"
    NO_BUILD = "no-build"
    ASK_USER = "ask-user"
    ORCHESTRATOR_DECIDES = "orchestrator-decides"
    BLOCK = "block"


class CompanyRunBootstrapVoteId(StrEnum):
    """Stable identifiers for votes required before company-run Team bootstrap."""

    RESEARCH_COMPLETION = "research_completion"
    PROCEED = "proceed"
    EXECUTIVE_GATE = "executive_gate"


class CompanyRunArtifactKind(StrEnum):
    """Durable company-run artifact classes."""

    STATE = "state"
    PHASE_LOG = "phase_log"
    ROSTER = "roster"
    DISCOVERY = "discovery"
    DECISION_REPORT = "decision_report"
    RESEARCH = "research"
    VOTE = "vote"
    PRD = "prd"
    TEST_SPEC = "test_spec"
    EXECUTION_BRIEF = "execution_brief"
    READINESS = "readiness"
    TEAM = "team"
    INTEGRATION = "integration"
    REVIEW = "review"
    RELEASE = "release"
    MEMORY = "memory"


class CompanyRunTeamLaunchStatus(StrEnum):
    """Outcomes for the OMX Team runtime leg."""

    LAUNCHED = "launched"
    COMPLETED = "completed"
    REQUIRES_AGENT_ACTION = "requires_agent_action"
    FAILED = "failed"


class CompanyRunTeamLaunchBlockerSignal(StrEnum):
    """Known native OMX Team launch outputs that require agent follow-up."""

    DIRTY_WORKTREE = "leader_workspace_dirty_for_worktrees"
    COMMIT_OR_STASH = "commit_or_stash_before_omx_team"
    WORKER_DID_NOT_BECOME_READY = "did not become ready"
    READY_PROMPT_TIMEOUT = "ready_prompt_timeout"
    STARTUP_PROMPT_TIMEOUT = "startup_prompt_timeout"
    WORKER_STARTUP_TIMEOUT = "worker_startup_timeout"
    STARTUP_TIMEOUT = "startup_timeout"
    CANNOT_START_TEAM = "cannot start team"
    WORKFLOW_OVERLAP = "unsupported workflow overlap"


class CompanyRunFinalStatus(StrEnum):
    """Company-run engine status before mapping to command actual-run status."""

    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"
    REQUIRES_AGENT_ACTION = "requires_agent_action"


class CompanyRunCouncilMode(StrEnum):
    """Company-run council/subagent execution mode."""

    CODEX = "codex"
    ARTIFACT = "artifact"


class CompanyRunTeamLaunchMode(StrEnum):
    """Company-run Team launch handling requested by the caller."""

    LAUNCH = "launch"
    HANDOFF = "handoff"
