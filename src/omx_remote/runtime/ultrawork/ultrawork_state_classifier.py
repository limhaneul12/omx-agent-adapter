from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.adapter_types.type_contract.ultrawork_contract_type import (
    ULTRAWORK_NON_TERMINAL_OUTCOMES,
    ULTRAWORK_NON_TERMINAL_PHASES,
    ULTRAWORK_TERMINAL_OUTCOMES,
    ULTRAWORK_TERMINAL_PHASES,
)
from omx_remote.shared.omx_enums.ultrawork_enums import (
    UltraworkRunOutcome,
    UltraworkRuntimePhase,
    UltraworkStateClassification,
)


def _normalize_token(value: object) -> str | None:
    """Handles normalize token.
    
    Args:
        value [object]: Function argument.
    
    Returns:
        str | None: Function return value.
    """
    token: str
    if not isinstance(value, str):
        return None

    token = value.strip().lower()
    normalized_token: str | None = token or None
    return normalized_token




class UltraworkStateTokenClassifier:
    """Normalizes and classifies individual Ultrawork state tokens."""

    @staticmethod
    def normalize_phase(phase_value: object) -> UltraworkRuntimePhase | None:
        """Normalize a raw phase marker into an Ultrawork phase enum.

        Args:
            phase_value: Raw phase value read from an Ultrawork state artifact.

        Returns:
            Matching Ultrawork phase enum, or ``None`` when unknown.
        """
        token: str | None = _normalize_token(phase_value)
        if token is None:
            return None

        try:
            phase = UltraworkRuntimePhase(token)
        except ValueError:
            return None

        return phase

    @staticmethod
    def normalize_outcome(outcome_value: object) -> UltraworkRunOutcome | None:
        """Normalize a raw outcome marker into an Ultrawork outcome enum.

        Args:
            outcome_value: Raw outcome value read from an Ultrawork state artifact.

        Returns:
            Matching Ultrawork outcome enum, or ``None`` when unknown.
        """
        token: str | None = _normalize_token(outcome_value)
        if token is None:
            return None

        try:
            outcome = UltraworkRunOutcome(token)
        except ValueError:
            return None

        return outcome

    @staticmethod
    def is_terminal_phase(phase_value: object) -> bool:
        """Return whether a raw phase value is terminal.

        Args:
            phase_value: Raw phase value read from state.

        Returns:
            ``True`` when the phase maps to a terminal Ultrawork phase.
        """
        phase: UltraworkRuntimePhase | None = UltraworkStateTokenClassifier.normalize_phase(
            phase_value
        )
        is_terminal_phase = bool(
            phase and phase in ULTRAWORK_TERMINAL_PHASES
        )
        return is_terminal_phase

    @staticmethod
    def is_terminal_outcome(outcome_value: object) -> bool:
        """Return whether a raw outcome value is terminal.

        Args:
            outcome_value: Raw outcome value read from state.

        Returns:
            ``True`` when the outcome maps to a terminal Ultrawork outcome.
        """
        outcome: UltraworkRunOutcome | None = UltraworkStateTokenClassifier.normalize_outcome(
            outcome_value
        )
        is_terminal_outcome = bool(
            outcome and outcome in ULTRAWORK_TERMINAL_OUTCOMES
        )
        return is_terminal_outcome

    @staticmethod
    def is_active_phase(phase_value: object) -> bool:
        """Return whether a raw phase value is resumable/non-terminal.

        Args:
            phase_value: Raw phase value read from state.

        Returns:
            ``True`` when the phase maps to a non-terminal Ultrawork phase.
        """
        phase: UltraworkRuntimePhase | None = UltraworkStateTokenClassifier.normalize_phase(
            phase_value
        )
        is_active_phase = bool(phase and phase in ULTRAWORK_NON_TERMINAL_PHASES)
        return is_active_phase

    @staticmethod
    def is_active_outcome(outcome_value: object) -> bool:
        """Return whether a raw outcome value is resumable/non-terminal.

        Args:
            outcome_value: Raw outcome value read from state.

        Returns:
            ``True`` when the outcome maps to a non-terminal Ultrawork outcome.
        """
        outcome: UltraworkRunOutcome | None = UltraworkStateTokenClassifier.normalize_outcome(
            outcome_value
        )
        is_active_outcome = bool(
            outcome and outcome in ULTRAWORK_NON_TERMINAL_OUTCOMES
        )
        return is_active_outcome



class UltraworkStateClassifier:
    """Classifies adapter-visible Ultrawork runtime state snapshots."""

    @staticmethod
    def classify_state_snapshot(
        state_payload: JsonObject,
    ) -> UltraworkStateClassification:
        """Classify one Ultrawork state payload for launch/resume preflight.

        Args:
            state_payload: Parsed Ultrawork state object.

        Returns:
            Adapter-owned Ultrawork state classification.
        """
        active_value: object | None = state_payload.get("active")

        if active_value is True:
            return UltraworkStateClassification.RESUMABLE

        if active_value is False:
            classification = UltraworkStateClassifier._classify_inactive_state(
                state_payload
            )
            return classification

        if active_value is not None and not isinstance(active_value, bool):
            return UltraworkStateClassification.STALE

        classification = UltraworkStateClassifier._classify_marker_state(state_payload)
        return classification

    @staticmethod
    def _classify_inactive_state(
        state_payload: JsonObject,
    ) -> UltraworkStateClassification:
        """Handles classify inactive state.
        
        Args:
            state_payload [JsonObject]: Function argument.
        
        Returns:
            UltraworkStateClassification: Function return value.
        """
        outcome_value: object | None = UltraworkStateClassifier._read_outcome_value(
            state_payload
        )
        phase_value: object | None = state_payload.get("current_phase")

        if UltraworkStateTokenClassifier.is_terminal_outcome(
            outcome_value
        ) or UltraworkStateTokenClassifier.is_terminal_phase(phase_value):
            return UltraworkStateClassification.TERMINAL

        if UltraworkStateTokenClassifier.is_active_outcome(
            outcome_value
        ) or UltraworkStateTokenClassifier.is_active_phase(phase_value):
            return UltraworkStateClassification.RESUMABLE

        return UltraworkStateClassification.STALE

    @staticmethod
    def _classify_marker_state(
        state_payload: JsonObject,
    ) -> UltraworkStateClassification:
        """Handles classify marker state.
        
        Args:
            state_payload [JsonObject]: Function argument.
        
        Returns:
            UltraworkStateClassification: Function return value.
        """
        outcome_value: object | None = UltraworkStateClassifier._read_outcome_value(
            state_payload
        )
        phase_value: object | None = state_payload.get("current_phase")

        if UltraworkStateTokenClassifier.is_terminal_outcome(outcome_value):
            return UltraworkStateClassification.TERMINAL

        if UltraworkStateTokenClassifier.is_active_outcome(
            outcome_value
        ) or UltraworkStateTokenClassifier.is_active_phase(phase_value):
            return UltraworkStateClassification.RESUMABLE

        if UltraworkStateTokenClassifier.is_terminal_phase(phase_value):
            return UltraworkStateClassification.TERMINAL

        return UltraworkStateClassification.STALE

    @staticmethod
    def _read_outcome_value(state_payload: JsonObject) -> object | None:
        """Handles read outcome value.
        
        Args:
            state_payload [JsonObject]: Function argument.
        
        Returns:
            object | None: Function return value.
        """
        outcome_value: object | None = state_payload.get("run_outcome")
        if outcome_value is None:
            outcome_value = state_payload.get("outcome")

        return outcome_value
