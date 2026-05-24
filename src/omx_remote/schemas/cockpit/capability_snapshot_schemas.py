from pydantic import Field

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class CockpitCapabilityCommand(StrictSchemaModel):
    """Represents availability evidence for one native command capability."""

    name: NonEmptyString
    available: bool
    detail: NonEmptyString


class CockpitRuntimeCapability(StrictSchemaModel):
    """Represents one runtime executable and its observed capabilities."""

    name: NonEmptyString
    available: bool
    executable_path: NonEmptyString | None = None
    version: NonEmptyString | None = None
    commands: tuple[CockpitCapabilityCommand, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()


class CockpitCapabilitiesSnapshot(StrictSchemaModel):
    """Represents Codex and OMX capability evidence for cockpit snapshots."""

    codex: CockpitRuntimeCapability
    omx: CockpitRuntimeCapability


class CockpitAgentConfigSummary(StrictSchemaModel):
    """Represents configured agent counts for cockpit snapshots."""

    config_path: NonEmptyString
    total_count: int = Field(ge=0)
    enabled_count: int = Field(ge=0)
    disabled_count: int = Field(ge=0)
    enabled_agent_ids: tuple[NonEmptyString, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()


class CockpitCommandRecipeSummary(StrictSchemaModel):
    """Represents command recipe counts for cockpit snapshots."""

    available_count: int = Field(ge=0)
    builtin_count: int = Field(ge=0)
    repo_count: int = Field(ge=0)
    qualified_ids: tuple[NonEmptyString, ...] = ()
    warnings: tuple[NonEmptyString, ...] = ()
