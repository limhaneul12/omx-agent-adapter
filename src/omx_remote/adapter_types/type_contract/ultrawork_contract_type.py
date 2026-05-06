from omx_remote.adapter_types.ultrawork_types import (
    UltraworkRunOutcomeSet,
    UltraworkRuntimePhaseSet,
)
from omx_remote.shared.omx_enums.ultrawork_enums import (
    UltraworkRunOutcome,
    UltraworkRuntimePhase,
)

ULTRAWORK_TERMINAL_PHASES: UltraworkRuntimePhaseSet = frozenset(
    {
        UltraworkRuntimePhase.COMPLETE,
        UltraworkRuntimePhase.COMPLETED,
        UltraworkRuntimePhase.FAILED,
        UltraworkRuntimePhase.CANCELLED,
    }
)
ULTRAWORK_NON_TERMINAL_PHASES: UltraworkRuntimePhaseSet = frozenset(
    {
        UltraworkRuntimePhase.STARTING,
        UltraworkRuntimePhase.RUNNING,
        UltraworkRuntimePhase.EXECUTING,
        UltraworkRuntimePhase.PLANNING,
        UltraworkRuntimePhase.ACTIVE,
        UltraworkRuntimePhase.PAUSED,
        UltraworkRuntimePhase.IDLE,
        UltraworkRuntimePhase.USER_INTERLUDE,
        UltraworkRuntimePhase.BLOCKED_ON_USER,
        UltraworkRuntimePhase.WAITING,
    }
)
ULTRAWORK_TERMINAL_OUTCOMES: UltraworkRunOutcomeSet = frozenset(
    {
        UltraworkRunOutcome.FINISH,
        UltraworkRunOutcome.BLOCKED_ON_USER,
        UltraworkRunOutcome.FAILED,
        UltraworkRunOutcome.CANCELLED,
        UltraworkRunOutcome.COMPLETE,
        UltraworkRunOutcome.COMPLETED,
        UltraworkRunOutcome.DONE,
        UltraworkRunOutcome.USER_INTERLUDE,
    }
)
ULTRAWORK_NON_TERMINAL_OUTCOMES: UltraworkRunOutcomeSet = frozenset(
    {
        UltraworkRunOutcome.CONTINUE,
        UltraworkRunOutcome.PROGRESS,
        UltraworkRunOutcome.RUNNING,
        UltraworkRunOutcome.ACTIVE,
    }
)
