"""Typed process-environment snapshot boundary for subprocess/MCP handoffs."""

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _environment_snapshot() -> dict[str, str]:
    """Capture current process environment values.

    Returns:
        dict[str, str]: Current process environment snapshot.
    """
    snapshot = dict(os.environ)
    return snapshot


class ProcessEnvironmentSettings(BaseSettings):
    """Typed process environment snapshot for runtime boundary handoffs.

    This is the only shared production contract that snapshots the full process
    environment. Feature-specific options should live in concept-owned settings
    or request schemas instead of being added here.
    """

    model_config = SettingsConfigDict(
        extra="ignore",
        frozen=True,
        validate_default=True,
    )

    environment_values: dict[str, str] = Field(
        default_factory=_environment_snapshot,
        exclude=True,
        repr=False,
    )

    def dynamic_environment_value(self, name: str) -> str | None:
        """Return a named value from the captured process environment.

        Args:
            name [str]: Environment variable name.

        Returns:
            str | None: Captured value when present.
        """
        if name not in self.environment_values:
            missing_value: None = None
            return missing_value
        value = self.environment_values[name]
        return value
