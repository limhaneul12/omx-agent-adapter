from enum import StrEnum

from omx_remote.adapter_types.json_types import JsonValue
from omx_remote.schemas.common_schemas import NonEmptyString, StrictSchemaModel


class ProbeSupportStatus(StrEnum):
    """Support status derived from one upstream probe."""

    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    EXPERIMENTAL = "experimental"
    UNKNOWN = "unknown"


class ProbeProcessOutput(StrictSchemaModel):
    """Represents raw process output supplied by a probe runner."""

    exit_code: int
    stdout: str
    stderr: str


class UpstreamProbeCommandResult(StrictSchemaModel):
    """Represents one upstream command contract probe result."""

    capability: NonEmptyString
    command: tuple[NonEmptyString, ...]
    exit_code: int
    stdout_summary: str
    stderr_summary: str
    parsed_json: JsonValue | None = None
    support_status: ProbeSupportStatus


class UpstreamProbeSuiteResult(StrictSchemaModel):
    """Represents a suite of upstream command contract probes."""

    suite_id: NonEmptyString
    target: NonEmptyString
    results: tuple[UpstreamProbeCommandResult, ...]

    @property
    def supported_count(self) -> int:
        """Count supported probe results.

        Returns:
            int: Number of supported probes.
        """
        count: int = sum(
            1
            for result in self.results
            if result.support_status == ProbeSupportStatus.SUPPORTED
        )
        return count

    @property
    def unsupported_count(self) -> int:
        """Count unsupported probe results.

        Returns:
            int: Number of unsupported probes.
        """
        count: int = sum(
            1
            for result in self.results
            if result.support_status == ProbeSupportStatus.UNSUPPORTED
        )
        return count


class ProbeStatusChange(StrictSchemaModel):
    """Represents one support-status change between fixture and current probe."""

    capability: NonEmptyString
    fixture_status: ProbeSupportStatus
    current_status: ProbeSupportStatus


class ProbeFixtureComparison(StrictSchemaModel):
    """Represents a fixture comparison result."""

    fixture_path: NonEmptyString
    current_suite_id: NonEmptyString
    matches: bool
    added_capabilities: tuple[NonEmptyString, ...] = ()
    removed_capabilities: tuple[NonEmptyString, ...] = ()
    status_changes: tuple[ProbeStatusChange, ...] = ()


class ProbeFixtureListResult(StrictSchemaModel):
    """Represents available sanitized probe fixtures."""

    fixtures: tuple[NonEmptyString, ...] = ()
