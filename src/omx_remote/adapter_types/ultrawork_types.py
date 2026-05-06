from omx_remote.shared.omx_enums.ultrawork_enums import (
    UltraworkRunOutcome,
    UltraworkRuntimePhase,
)

type UltraworkRuntimePhaseSet = frozenset[UltraworkRuntimePhase]
type UltraworkRunOutcomeSet = frozenset[UltraworkRunOutcome]
