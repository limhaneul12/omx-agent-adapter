"""Ralph Team owner-preflight settings."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RalphOwnerPreflightSettings(BaseSettings):
    """Environment-backed fallback for locating the installed OMX dist root."""

    model_config = SettingsConfigDict(
        extra="ignore",
        frozen=True,
        validate_default=True,
    )

    omx_dist_root: Path | None = Field(
        default=None,
        validation_alias="COMX_AGENT_OMX_DIST_ROOT",
    )
