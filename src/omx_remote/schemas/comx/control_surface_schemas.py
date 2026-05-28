from enum import StrEnum

from pydantic import Field

from omx_remote.schemas.commands.command_recipe_schemas import CommandCatalogEntry
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class ComxSurfaceKind(StrEnum):
    """Kinds of command surfaces that comx-agent exposes."""

    NATIVE = "native"
    COMPOSED_RECIPE = "composed_recipe"


class ComxNativeCommand(StrictSchemaModel):
    """Represents one direct comx-agent command surface."""

    name: NonEmptyString
    kind: ComxSurfaceKind = ComxSurfaceKind.NATIVE
    description: NonEmptyString
    read_only_default: bool
    mutates_runtime: bool


class ComxControlSurfaceInventory(StrictSchemaModel):
    """Represents the complete comx-agent command surface inventory."""

    product_name: NonEmptyString
    compatibility_aliases: tuple[NonEmptyString, ...]
    native_commands: tuple[ComxNativeCommand, ...]
    composed_commands: tuple[CommandCatalogEntry, ...]
    native_count: int = Field(ge=0)
    composed_count: int = Field(ge=0)
    summary: NonEmptyString
