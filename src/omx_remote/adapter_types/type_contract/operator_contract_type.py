from omx_remote.shared.omx_enums.multi_operator_enums import ManagedInterventionAction
from omx_remote.shared.omx_enums.operator_enums import OperatorLoopState

type ManagedInterventionActionSet = frozenset[ManagedInterventionAction]
type OperatorLoopStateSet = frozenset[OperatorLoopState]

ACTIONABLE_NEXT_ACTIONS: ManagedInterventionActionSet = frozenset(
    {
        ManagedInterventionAction.LAUNCH,
        ManagedInterventionAction.RESUME,
        ManagedInterventionAction.RETRY,
        ManagedInterventionAction.CLEANUP,
        ManagedInterventionAction.CANCEL,
        ManagedInterventionAction.ESCALATE,
    }
)
ACTIVE_LOOP_STATES: OperatorLoopStateSet = frozenset(
    {
        OperatorLoopState.SUCCESS,
        OperatorLoopState.RESUMABLE_LATER,
        OperatorLoopState.BLOCKED_APPROVAL_NEEDED,
        OperatorLoopState.RETRYABLE_AFTER_CLEANUP,
    }
)
BLOCKING_LOOP_STATES: OperatorLoopStateSet = frozenset(
    {
        OperatorLoopState.TERMINAL_FAILURE,
        OperatorLoopState.STALE_STATE_FAILURE,
        OperatorLoopState.DIRTY_WORKSPACE_FAILURE,
        OperatorLoopState.BLOCKED_APPROVAL_NEEDED,
    }
)
