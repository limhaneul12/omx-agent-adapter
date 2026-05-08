from dataclasses import dataclass

from omx_remote.adapter_types.json_types import JsonValue


@dataclass(frozen=True, slots=True)
class TeamApiDecodedEnvelope:
    """Represents the decoded top-level team-api transport envelope."""

    ok: bool
    # The ok flag selects the operation-specific data/error loader that narrows this.
    data: JsonValue = None
    error: JsonValue = None
