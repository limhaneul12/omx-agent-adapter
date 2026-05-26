from enum import StrEnum

from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class ComxResearchSource(StrEnum):
    """Source classes available to a comx-agent research workflow."""

    REPO = "repo"
    OFFICIAL_DOCS = "official_docs"
    WEB = "web"
    MCP = "mcp"
    ALEXANDRIA = "alexandria"
    TEAM = "team"


class ComxResearchWorkflowPlan(StrictSchemaModel):
    """Represents a staged deep-research workflow artifact."""

    research_id: NonEmptyString
    objective: NonEmptyString
    created_at: NonEmptyString
    status: NonEmptyString
    sources: tuple[ComxResearchSource, ...]
    ambiguity_questions: tuple[NonEmptyString, ...]
    verification_steps: tuple[NonEmptyString, ...]
    handoff_recommendation: NonEmptyString
    artifact_path: NonEmptyString
    warnings: tuple[NonEmptyString, ...] = ()
