from typing import Literal, TypedDict

from omx_remote.shared.omx_enums.ralph_enums import (
    TeamAdminAggregationPolicy,
    TeamAdminCompletionPolicy,
    TeamAdminMergePolicy,
    TeamWorkerAuthorizationPolicy,
)


class RalphWorkerAuthorizationPayload(TypedDict):
    """Represents the stable Team DAG authorization payload emitted by Ralph."""

    policy: TeamWorkerAuthorizationPolicy
    allowed_commands: list[str]
    forbidden_commands: list[str]
    requires_human_for: list[str]
    requires_llm_review_for: list[str]


class RalphTeamDagWorkerPolicyPayload(TypedDict):
    """Represents the stable Team DAG worker-count policy payload emitted by Ralph."""

    requested_count: int
    count_source: Literal["plan-suggested"]
    strict_max_count: bool


class RalphTeamDagNodePayload(TypedDict):
    """Represents one stable worker node in a Ralph-owned Team DAG handoff."""

    id: str
    subject: str
    description: str
    role: str
    owner: str
    lane: str
    filePaths: list[str]
    depends_on: list[str]
    authorization: RalphWorkerAuthorizationPayload
    acceptance: list[str]


class RalphTeamDagAdminPolicyPayload(TypedDict):
    """Represents the stable Team Admin policy embedded in a Ralph Team DAG."""

    admin_id: str
    aggregation_policy: TeamAdminAggregationPolicy
    merge_policy: TeamAdminMergePolicy
    completion_policy: TeamAdminCompletionPolicy
    requires_human_for: list[str]
    requires_llm_review_for: list[str]
    final_report_required: bool


class RalphTeamDagPayload(TypedDict):
    """Represents the stable JSON Team DAG handoff payload emitted by Ralph."""

    schema_version: int
    plan_slug: str
    source_prd: str
    worker_policy: RalphTeamDagWorkerPolicyPayload
    admin_policy: RalphTeamDagAdminPolicyPayload
    nodes: list[RalphTeamDagNodePayload]
