from pydantic import model_validator

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class ProcessEnvironmentOverride(StrictSchemaModel):
    """One explicit subprocess environment override."""

    name: NonEmptyString
    value: NonEmptyString


class ProcessEnvironmentOverrides(StrictSchemaModel):
    """Immutable subprocess environment override bundle."""

    values: tuple[ProcessEnvironmentOverride, ...]

    @model_validator(mode="after")
    def _validate_unique_names(self) -> "ProcessEnvironmentOverrides":
        """Reject duplicate environment override names.

        Returns:
            ProcessEnvironmentOverrides: Validated override bundle.
        """
        if not self.values:
            raise ValueError("process environment overrides require at least one value")
        names = [override.name for override in self.values]
        if len(names) != len(set(names)):
            raise ValueError("process environment override names must be unique")
        return self

    def as_environment_mapping(self) -> dict[str, str]:
        """Return overrides in the mapping shape required by subprocess.

        Returns:
            dict[str, str]: Environment override mapping.
        """
        mapping = {override.name: override.value for override in self.values}
        return mapping
