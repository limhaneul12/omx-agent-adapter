from omx_remote.shared.omx_enums.ralph_enums import RalphRunOutcome, RalphRuntimePhase

type RalphRuntimePhaseSet = frozenset[RalphRuntimePhase]
type RalphRunOutcomeSet = frozenset[RalphRunOutcome]

RALPH_TERMINAL_PHASES: RalphRuntimePhaseSet = frozenset(
    {
        RalphRuntimePhase.COMPLETE,
        RalphRuntimePhase.COMPLETED,
        RalphRuntimePhase.FAILED,
        RalphRuntimePhase.CANCELLED,
    }
)
RALPH_NON_TERMINAL_PHASES: RalphRuntimePhaseSet = frozenset(
    {
        RalphRuntimePhase.STARTING,
        RalphRuntimePhase.RUNNING,
        RalphRuntimePhase.EXECUTING,
        RalphRuntimePhase.PLANNING,
        RalphRuntimePhase.ACTIVE,
        RalphRuntimePhase.PAUSED,
        RalphRuntimePhase.IDLE,
        RalphRuntimePhase.USER_INTERLUDE,
        RalphRuntimePhase.BLOCKED_ON_USER,
        RalphRuntimePhase.WAITING,
    }
)
RALPH_TERMINAL_OUTCOMES: RalphRunOutcomeSet = frozenset(
    {
        RalphRunOutcome.FINISH,
        RalphRunOutcome.BLOCKED_ON_USER,
        RalphRunOutcome.FAILED,
        RalphRunOutcome.CANCELLED,
        RalphRunOutcome.COMPLETE,
        RalphRunOutcome.COMPLETED,
        RalphRunOutcome.DONE,
        RalphRunOutcome.USER_INTERLUDE,
    }
)
RALPH_NON_TERMINAL_OUTCOMES: RalphRunOutcomeSet = frozenset(
    {
        RalphRunOutcome.CONTINUE,
        RalphRunOutcome.PROGRESS,
        RalphRunOutcome.RUNNING,
        RalphRunOutcome.ACTIVE,
    }
)
