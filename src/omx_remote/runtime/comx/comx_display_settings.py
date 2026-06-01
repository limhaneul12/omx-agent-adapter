"""COMX display settings owned by the TUI/status rendering slice."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ComxDisplaySettings(BaseSettings):
    """Environment-backed COMX display hints with UX-safe defaults."""

    model_config = SettingsConfigDict(
        extra="ignore",
        frozen=True,
        validate_default=True,
    )

    model_label: str = Field(
        default="gpt-5.5 xhigh",
        validation_alias="COMX_AGENT_MODEL",
    )
    codex_sandbox: str | None = Field(
        default=None,
        validation_alias="CODEX_SANDBOX",
    )
    omx_permissions: str | None = Field(
        default=None,
        validation_alias="OMX_PERMISSIONS",
    )
