from pathlib import Path

import orjson

from omx_remote.schemas.probes.upstream_probe_schemas import (
    ProbeFixtureComparison,
    ProbeFixtureListResult,
    ProbeStatusChange,
    UpstreamProbeCommandResult,
    UpstreamProbeSuiteResult,
)

FIXTURE_ROOT = Path("tests/fixtures/upstream_contracts")


def _read_fixture(path: str | Path) -> UpstreamProbeSuiteResult:
    """Read one probe fixture.

    Args:
        path [str | Path]: Fixture JSON path.

    Returns:
        UpstreamProbeSuiteResult: Parsed fixture.
    """
    parsed_json: object = orjson.loads(Path(path).read_bytes())
    fixture = UpstreamProbeSuiteResult.model_validate(parsed_json)
    return fixture


def _capability_map(
    result: UpstreamProbeSuiteResult,
) -> dict[str, UpstreamProbeCommandResult]:
    """Build a capability-indexed result map.

    Args:
        result [UpstreamProbeSuiteResult]: Suite result to index.

    Returns:
        dict[str, UpstreamProbeCommandResult]: Probe results by capability.
    """
    capability_map: dict[str, UpstreamProbeCommandResult] = {
        probe.capability: probe for probe in result.results
    }
    return capability_map


def compare_probe_fixture(
    fixture_path: str | Path,
    current: UpstreamProbeSuiteResult,
) -> ProbeFixtureComparison:
    """Compare a stored fixture with current probe evidence.

    Args:
        fixture_path [str | Path]: Fixture JSON path.
        current [UpstreamProbeSuiteResult]: Current suite result.

    Returns:
        ProbeFixtureComparison: Added, removed, and changed capabilities.
    """
    fixture: UpstreamProbeSuiteResult = _read_fixture(fixture_path)
    fixture_by_capability: dict[str, UpstreamProbeCommandResult] = _capability_map(fixture)
    current_by_capability: dict[str, UpstreamProbeCommandResult] = _capability_map(current)
    fixture_capabilities: set[str] = set(fixture_by_capability)
    current_capabilities: set[str] = set(current_by_capability)
    added_capabilities: tuple[str, ...] = tuple(
        sorted(current_capabilities - fixture_capabilities)
    )
    removed_capabilities: tuple[str, ...] = tuple(
        sorted(fixture_capabilities - current_capabilities)
    )
    status_changes: tuple[ProbeStatusChange, ...] = tuple(
        ProbeStatusChange(
            capability=capability,
            fixture_status=fixture_by_capability[capability].support_status,
            current_status=current_by_capability[capability].support_status,
        )
        for capability in sorted(fixture_capabilities & current_capabilities)
        if fixture_by_capability[capability].support_status
        != current_by_capability[capability].support_status
    )
    comparison = ProbeFixtureComparison(
        fixture_path=str(fixture_path),
        current_suite_id=current.suite_id,
        matches=not added_capabilities and not removed_capabilities and not status_changes,
        added_capabilities=added_capabilities,
        removed_capabilities=removed_capabilities,
        status_changes=status_changes,
    )
    return comparison


def list_probe_fixtures(root: str | Path = FIXTURE_ROOT) -> ProbeFixtureListResult:
    """List sanitized upstream contract fixtures.

    Args:
        root [str | Path]: Fixture root path.

    Returns:
        ProbeFixtureListResult: Fixture paths.
    """
    root_path: Path = Path(root)
    if not root_path.exists():
        empty_result = ProbeFixtureListResult(fixtures=())
        return empty_result

    fixtures: tuple[str, ...] = tuple(
        str(path) for path in sorted(root_path.rglob("*.json"))
    )
    result = ProbeFixtureListResult(fixtures=fixtures)
    return result
