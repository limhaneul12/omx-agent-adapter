from typing import Self

from pydantic import model_validator

from omx_remote.schemas.common_schemas import (
    NonEmptyString,
    StrictRootSchemaModel,
    StrictSchemaModel,
)
from omx_remote.schemas.operator_action_schemas import OperatorActionResult
from omx_remote.shared.omx_enums.multi_operator_enums import (
    ManagedFlowKind,
    ManagedInterventionAction,
)


class ManagedOmxRepo(StrictSchemaModel):
    """Represents one repo-scoped OMX workspace tracked by the multi-operator layer."""

    repo_id: NonEmptyString
    repo_root: NonEmptyString


class ManagedOmxFlow(StrictSchemaModel):
    """Represents one controllable OMX-backed flow inside a tracked repo."""

    flow_id: NonEmptyString
    repo_id: NonEmptyString
    flow_kind: ManagedFlowKind
    flow_name: NonEmptyString
    team_name: NonEmptyString | None = None
    last_result: OperatorActionResult | None = None


class ManagedOmxRepoCollection(StrictRootSchemaModel[tuple[ManagedOmxRepo, ...]]):
    """Root schema for unique repo-scoped OMX workspaces."""

    def __len__(self) -> int:
        """Return the number of tracked repos.

        Returns:
            int: Number of repo contracts in the collection.
        """
        repo_count: int = len(self.root)
        return repo_count

    def __getitem__(self, index: int) -> ManagedOmxRepo:
        """Return one tracked repo by index.

        Args:
            index [int]: Position in the repo collection.

        Returns:
            ManagedOmxRepo: Repo contract at the requested index.
        """
        repo: ManagedOmxRepo = self.root[index]
        return repo

    @model_validator(mode="after")
    def validate_unique_repo_ids(self) -> Self:
        """Reject duplicate repo ids.

        Returns:
            Self: Validated repo collection.
        """
        repo_ids: tuple[str, ...] = tuple(repo.repo_id for repo in self.root)
        if len(set(repo_ids)) != len(repo_ids):
            raise ValueError("Managed repo ids must be unique.")

        return self


class ManagedOmxFlowCollection(StrictRootSchemaModel[tuple[ManagedOmxFlow, ...]]):
    """Root schema for unique controllable OMX-backed flows."""

    def __len__(self) -> int:
        """Return the number of tracked flows.

        Returns:
            int: Number of flow contracts in the collection.
        """
        flow_count: int = len(self.root)
        return flow_count

    def __getitem__(self, index: int) -> ManagedOmxFlow:
        """Return one tracked flow by index.

        Args:
            index [int]: Position in the flow collection.

        Returns:
            ManagedOmxFlow: Flow contract at the requested index.
        """
        flow: ManagedOmxFlow = self.root[index]
        return flow

    @model_validator(mode="after")
    def validate_unique_flow_ids(self) -> Self:
        """Reject duplicate flow ids.

        Returns:
            Self: Validated flow collection.
        """
        flow_ids: tuple[str, ...] = tuple(flow.flow_id for flow in self.root)
        if len(set(flow_ids)) != len(flow_ids):
            raise ValueError("Managed flow ids must be unique.")

        return self


class ManagedFlowIdCollection(StrictRootSchemaModel[tuple[NonEmptyString, ...]]):
    """Root schema for unique managed flow id buckets."""

    def __len__(self) -> int:
        """Return the number of flow ids.

        Returns:
            int: Number of flow ids in the collection.
        """
        flow_id_count: int = len(self.root)
        return flow_id_count

    def __getitem__(self, index: int) -> str:
        """Return one flow id by index.

        Args:
            index [int]: Position in the flow id collection.

        Returns:
            str: Flow id at the requested index.
        """
        flow_id: str = self.root[index]
        return flow_id

    def __contains__(self, flow_id: object) -> bool:
        """Return whether the bucket contains a flow id.

        Args:
            flow_id [object]: Candidate flow id value.

        Returns:
            bool: True when the candidate is present.
        """
        contains_flow_id: bool = flow_id in self.root
        return contains_flow_id

    def __eq__(self, other: object) -> bool:
        """Compare flow id buckets against list or tuple values.

        Args:
            other [object]: Candidate value to compare with this collection.

        Returns:
            bool: True when the ordered flow ids match.
        """
        if isinstance(other, list | tuple):
            matches_sequence: bool = tuple(other) == self.root
            return matches_sequence

        matches_model: bool = super().__eq__(other)
        return matches_model

    @model_validator(mode="after")
    def validate_unique_flow_ids(self) -> Self:
        """Reject duplicate flow ids.

        Returns:
            Self: Validated flow id collection.
        """
        flow_ids: tuple[str, ...] = tuple(self.root)
        if len(set(flow_ids)) != len(flow_ids):
            raise ValueError("Managed flow id bucket values must be unique.")

        return self


class FlowSelector(StrictSchemaModel):
    """Represents one typed selector for a repo-scoped managed flow."""

    repo_id: NonEmptyString
    flow_id: NonEmptyString


class FlowInterventionRequest(StrictSchemaModel):
    """Represents one typed intervention request for a managed flow."""

    selector: FlowSelector
    requested_action: ManagedInterventionAction


class MultiOperatorSnapshotReadRequest(StrictSchemaModel):
    """Represents one request to project repo-scoped OMX flow status."""

    repo_id: NonEmptyString
    repo_root: NonEmptyString
    team_names: tuple[NonEmptyString, ...] = ()


class MultiOperatorSnapshot(StrictSchemaModel):
    """Represents one aggregated view of all repo-scoped managed OMX flows."""

    repos: ManagedOmxRepoCollection
    flows: ManagedOmxFlowCollection
    active_flow_ids: ManagedFlowIdCollection
    launchable_flow_ids: ManagedFlowIdCollection
    resumable_flow_ids: ManagedFlowIdCollection
    cleanup_flow_ids: ManagedFlowIdCollection
    terminal_flow_ids: ManagedFlowIdCollection

    @model_validator(mode="after")
    def validate_bucket_ids_reference_known_flows(self) -> Self:
        """Reject bucket flow ids that are not present in the flow collection.

        Returns:
            Self: Validated multi-operator snapshot.
        """
        known_flow_ids: set[str] = {flow.flow_id for flow in self.flows.root}
        bucket_names: tuple[str, ...] = (
            "active_flow_ids",
            "launchable_flow_ids",
            "resumable_flow_ids",
            "cleanup_flow_ids",
            "terminal_flow_ids",
        )
        bucket_name: str
        for bucket_name in bucket_names:
            bucket: ManagedFlowIdCollection = getattr(self, bucket_name)
            unknown_flow_ids: list[str] = [
                flow_id for flow_id in bucket.root if flow_id not in known_flow_ids
            ]
            if unknown_flow_ids:
                raise ValueError(
                    f"{bucket_name} contains unknown flow ids: {', '.join(unknown_flow_ids)}"
                )

        return self
