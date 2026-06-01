from omx_remote.adapter_types.json_types import JsonObject
from omx_remote.adapter_types.type_contract.ralph_contract_type import (
    RALPH_NON_TERMINAL_OUTCOMES,
    RALPH_NON_TERMINAL_PHASES,
    RALPH_TERMINAL_OUTCOMES,
    RALPH_TERMINAL_PHASES,
)
from omx_remote.shared.omx_enums.ralph_enums import (
    RalphRunOutcome,
    RalphRuntimePhase,
    RalphStateClassification,
)


def normalize_ralph_state_token(value: object) -> str | None:
    """Normalizes one raw Ralph state marker token.

    Args:
        value [object]: Raw value loaded from a Ralph state artifact.

    Returns:
        str | None: Lowercase non-blank token, or `None` when unavailable.
    """
    if not isinstance(value, str):
        return None

    token: str = value.strip().lower()
    return token or None


class RalphStateClassifier:
    """Classifies adapter-visible Ralph runtime state markers."""

    @staticmethod
    def normalize_phase(phase_value: object) -> RalphRuntimePhase | None:
        """Normalizes a raw Ralph phase marker.

        Args:
            phase_value [object]: Raw phase value loaded from state.

        Returns:
            RalphRuntimePhase | None: Parsed phase enum, or `None` for missing/unknown values.
        """
        normalized_phase: str | None = normalize_ralph_state_token(phase_value)
        if normalized_phase is None:
            return None

        try:
            parsed_phase: RalphRuntimePhase = RalphRuntimePhase(normalized_phase)
        except ValueError:
            return None

        return parsed_phase

    @staticmethod
    def normalize_outcome(outcome_value: object) -> RalphRunOutcome | None:
        """Normalizes a raw Ralph outcome marker.

        Args:
            outcome_value [object]: Raw outcome value loaded from state.

        Returns:
            RalphRunOutcome | None: Parsed outcome enum, or `None` for missing/unknown values.
        """
        normalized_outcome: str | None = normalize_ralph_state_token(outcome_value)
        if normalized_outcome is None:
            return None

        try:
            parsed_outcome: RalphRunOutcome = RalphRunOutcome(normalized_outcome)
        except ValueError:
            return None

        return parsed_outcome

    @classmethod
    def is_terminal_phase(cls, phase_value: object) -> bool:
        """Checks whether a raw phase marker is terminal.

        Args:
            phase_value [object]: Raw phase value loaded from state.

        Returns:
            bool: `True` when the phase is a terminal Ralph phase.
        """
        phase: RalphRuntimePhase | None = cls.normalize_phase(phase_value)
        terminal_phase: bool = phase in RALPH_TERMINAL_PHASES
        return terminal_phase

    @classmethod
    def is_terminal_outcome(cls, outcome_value: object) -> bool:
        """Checks whether a raw outcome marker is terminal.

        Args:
            outcome_value [object]: Raw outcome value loaded from state.

        Returns:
            bool: `True` when the outcome is a terminal Ralph outcome.
        """
        outcome: RalphRunOutcome | None = cls.normalize_outcome(outcome_value)
        terminal_outcome: bool = outcome in RALPH_TERMINAL_OUTCOMES
        return terminal_outcome

    @classmethod
    def is_active_phase(cls, phase_value: object) -> bool:
        """Checks whether a raw phase marker is active/resumable.

        Args:
            phase_value [object]: Raw phase value loaded from state.

        Returns:
            bool: `True` when the phase is a non-terminal Ralph phase.
        """
        phase: RalphRuntimePhase | None = cls.normalize_phase(phase_value)
        active_phase: bool = phase in RALPH_NON_TERMINAL_PHASES
        return active_phase

    @classmethod
    def is_active_outcome(cls, outcome_value: object) -> bool:
        """Checks whether a raw outcome marker is active/resumable.

        Args:
            outcome_value [object]: Raw outcome value loaded from state.

        Returns:
            bool: `True` when the outcome is a non-terminal Ralph outcome.
        """
        outcome: RalphRunOutcome | None = cls.normalize_outcome(outcome_value)
        active_outcome: bool = outcome in RALPH_NON_TERMINAL_OUTCOMES
        return active_outcome

    @classmethod
    def classify_state_snapshot(
        cls,
        state_payload: JsonObject,
    ) -> RalphStateClassification:
        """Classifies a Ralph state artifact as resumable, terminal, or stale.

        Args:
            state_payload [JsonObject]: Raw state payload loaded from `.omx/state`.

        Returns:
            RalphStateClassification: Adapter-visible Ralph state classification.
        """
        active_value: object | None = state_payload.get("active")

        if active_value is True:
            return RalphStateClassification.RESUMABLE
        if active_value is False:
            return cls._classify_inactive_state(state_payload)
        if active_value is not None and not isinstance(active_value, bool):
            return RalphStateClassification.STALE

        unknown_active_state: RalphStateClassification = cls._classify_marker_state(
            state_payload
        )
        return unknown_active_state

    @classmethod
    def _classify_inactive_state(
        cls,
        state_payload: JsonObject,
    ) -> RalphStateClassification:
        """Classifies an explicitly inactive Ralph state payload.

        Args:
            state_payload [JsonObject]: Raw state payload with `active=false`.

        Returns:
            RalphStateClassification: Terminal, resumable, or stale classification.
        """
        outcome_value: object | None = cls._read_outcome_value(state_payload)
        phase_value: object | None = state_payload.get("current_phase")

        if cls.is_terminal_outcome(outcome_value) or cls.is_terminal_phase(phase_value):
            return RalphStateClassification.TERMINAL
        if cls.is_active_outcome(outcome_value) or cls.is_active_phase(phase_value):
            return RalphStateClassification.RESUMABLE

        return RalphStateClassification.STALE

    @classmethod
    def _classify_marker_state(
        cls,
        state_payload: JsonObject,
    ) -> RalphStateClassification:
        """Classifies a Ralph state payload using phase/outcome markers only.

        Args:
            state_payload [JsonObject]: Raw state payload without a boolean `active` marker.

        Returns:
            RalphStateClassification: Terminal, resumable, or stale classification.
        """
        outcome_value: object | None = cls._read_outcome_value(state_payload)
        phase_value: object | None = state_payload.get("current_phase")

        if cls.is_terminal_outcome(outcome_value):
            return RalphStateClassification.TERMINAL
        if cls.is_active_outcome(outcome_value) or cls.is_active_phase(phase_value):
            return RalphStateClassification.RESUMABLE
        if cls.is_terminal_phase(phase_value):
            return RalphStateClassification.TERMINAL

        return RalphStateClassification.STALE

    @staticmethod
    def _read_outcome_value(state_payload: JsonObject) -> object | None:
        """Reads the supported Ralph outcome marker from state payloads.

        Args:
            state_payload [JsonObject]: Raw state payload.

        Returns:
            object | None: Raw `run_outcome` or fallback `outcome` value.
        """
        outcome_value: object | None = state_payload.get("run_outcome")
        if outcome_value is None:
            outcome_value = state_payload.get("outcome")

        return outcome_value


def classify_ralph_state_snapshot(
    state_payload: JsonObject,
) -> RalphStateClassification:
    """Classifies Ralph state as resumable, terminal, or stale.

    Args:
        state_payload [JsonObject]: Raw state payload loaded from `.omx/state`.

    Returns:
        RalphStateClassification: Adapter-visible Ralph state classification.
    """
    state_classification: RalphStateClassification = (
        RalphStateClassifier.classify_state_snapshot(state_payload)
    )
    return state_classification
