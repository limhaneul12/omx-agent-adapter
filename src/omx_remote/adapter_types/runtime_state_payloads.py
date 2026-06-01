"""Typed outbound payload contracts for OMX state commands."""

from typing_extensions import TypedDict


class RuntimeModePayload(TypedDict, closed=True):
    """Represents an OMX state command payload keyed by mode."""

    mode: str
