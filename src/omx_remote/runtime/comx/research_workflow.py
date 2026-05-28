import re
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import orjson

from omx_remote.schemas.comx.research_workflow_schemas import (
    ComxResearchSource,
    ComxResearchWorkflowPlan,
)

RESEARCH_ARTIFACT_ROOT = ".comx-agent/research"
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    """Create a safe artifact slug.

    Args:
        value [str]: Source text.

    Returns:
        str: Lowercase slug.
    """
    lowered: str = value.strip().lower()
    slug: str = SLUG_PATTERN.sub("-", lowered).strip("-")
    if not slug:
        slug = "research"
    return slug[:48]


def _artifact_path(cwd: Path, research_id: str) -> Path:
    """Resolve a research artifact path.

    Args:
        cwd [Path]: Workspace root.
        research_id [str]: Research id.

    Returns:
        Path: Artifact path.
    """
    root: Path = cwd / RESEARCH_ARTIFACT_ROOT
    return root / f"{research_id}.json"


def _unique_artifact_target(cwd: Path, research_id: str) -> tuple[str, Path]:
    """Resolve a research id/path pair without overwriting artifacts.

    Args:
        cwd [Path]: Workspace root.
        research_id [str]: Preferred research id.

    Returns:
        tuple[str, Path]: Unique research id and path.
    """
    candidate_id: str = research_id
    candidate_path: Path = _artifact_path(cwd, candidate_id)
    counter = 2
    while candidate_path.exists():
        candidate_id = f"{research_id}-{counter}"
        candidate_path = _artifact_path(cwd, candidate_id)
        counter += 1
    return candidate_id, candidate_path


def create_research_workflow_plan(
    cwd: str | Path,
    objective: str,
    include_team: bool = True,
    include_alexandria: bool = True,
) -> ComxResearchWorkflowPlan:
    """Create and persist a staged deep-research plan artifact.

    Args:
        cwd [str | Path]: Workspace root.
        objective [str]: Research objective.
        include_team [bool]: Whether Team is an intended source class.
        include_alexandria [bool]: Whether Alexandria memory is an intended source class.

    Returns:
        ComxResearchWorkflowPlan: Persisted plan.
    """
    normalized_objective: str = objective.strip()
    if not normalized_objective:
        raise ValueError("/research requires an objective, for example: /research compare Codex MCP UX")

    workspace: Path = Path(cwd)
    created_at_datetime: datetime = datetime.now(UTC)
    created_at: str = created_at_datetime.isoformat()
    created_at_id: str = created_at_datetime.strftime("%Y%m%dT%H%M%S%fZ")
    digest: str = sha256(normalized_objective.encode("utf-8")).hexdigest()[:10]
    research_id: str = f"{created_at_id}-{_slugify(normalized_objective)}-{digest}"
    research_id, artifact_path = _unique_artifact_target(workspace, research_id)

    sources: list[ComxResearchSource] = [
        ComxResearchSource.REPO,
        ComxResearchSource.OFFICIAL_DOCS,
        ComxResearchSource.WEB,
        ComxResearchSource.MCP,
    ]
    if include_alexandria:
        sources.append(ComxResearchSource.ALEXANDRIA)
    if include_team:
        sources.append(ComxResearchSource.TEAM)

    plan = ComxResearchWorkflowPlan(
        research_id=research_id,
        objective=normalized_objective,
        created_at=created_at,
        status="planned",
        sources=tuple(sources),
        ambiguity_questions=(
            "What decision should this research unblock?",
            "Which sources are authoritative and which are only inspiration?",
            "Which MCP servers or private data sources are allowed?",
        ),
        verification_steps=(
            "Prefer official/upstream evidence before secondary summaries.",
            "Separate public web evidence from private MCP/Alexandria evidence.",
            "Record source paths, command outputs, and verification commands.",
            "Run a critic pass before implementation handoff.",
        ),
        handoff_recommendation=(
            "After evidence is collected, create or update an Ultragoal story and "
            "checkpoint with the research artifact path."
        ),
        artifact_path=str(artifact_path),
        warnings=(
            "Plan only: no external research tools were executed by this command.",
            "Do not expose secrets from MCP env values, headers, or Alexandria notes.",
        ),
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(
        orjson.dumps(plan.model_dump(mode="json"), option=orjson.OPT_INDENT_2)
    )
    return plan
