"""GitHub PR status credential settings owned by the GitHub cockpit source."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitHubCredentialSettings(BaseSettings):
    """Credential fallback contract for GitHub PR status evidence.

    Git credential storage remains preferred. This settings contract only owns
    conventional non-interactive token fallbacks for environments where git
    credential helpers are unavailable.
    """

    model_config = SettingsConfigDict(
        extra="ignore",
        frozen=True,
        validate_default=True,
    )

    token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("GITHUB_TOKEN", "GH_TOKEN"),
    )

    def normalized_token(self) -> str | None:
        """Return the configured token after blank-string normalization.

        Returns:
            str | None: Non-empty token when configured.
        """
        if self.token is None:
            missing_token: None = None
            return missing_token
        stripped_token = self.token.strip()
        if stripped_token == "":
            blank_token: None = None
            return blank_token
        token = stripped_token
        return token
