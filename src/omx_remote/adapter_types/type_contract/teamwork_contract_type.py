from omx_remote.shared.omx_enums.teamwork_enums import TeamEventType

type TeamEventTypeSet = frozenset[TeamEventType]

TEAM_DISPATCH_EVENT_TYPES: TeamEventTypeSet = frozenset(
    {
        TeamEventType.DISPATCH_QUEUED,
        TeamEventType.HANDOFF_SUBMITTED,
        TeamEventType.HOOK_RECEIPT,
        TeamEventType.MESSAGE_RECEIVED,
        TeamEventType.TASK_CREATED,
    }
)
TEAM_COMPLETION_EVENT_TYPES: TeamEventTypeSet = frozenset({TeamEventType.TASK_COMPLETED})
