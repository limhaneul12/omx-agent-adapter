from pathlib import Path

from omx_remote.runtime.probes.probe_fixture_comparator import compare_probe_fixture
from omx_remote.schemas.upstream_probe_schemas import (
    ProbeSupportStatus,
    UpstreamProbeCommandResult,
    UpstreamProbeSuiteResult,
)


def _probe(capability: str, status: ProbeSupportStatus) -> UpstreamProbeCommandResult:
    return UpstreamProbeCommandResult(
        capability=capability,
        command=("tool", capability, "--help"),
        exit_code=0 if status == ProbeSupportStatus.SUPPORTED else 1,
        stdout_summary="ok" if status == ProbeSupportStatus.SUPPORTED else "",
        stderr_summary="" if status == ProbeSupportStatus.SUPPORTED else "missing",
        parsed_json=None,
        support_status=status,
    )


def test_compare_probe_fixture_reports_added_removed_and_changed(
    tmp_path: Path,
) -> None:
    fixture = UpstreamProbeSuiteResult(
        suite_id="omx-basic",
        target="omx",
        results=(
            _probe("version", ProbeSupportStatus.SUPPORTED),
            _probe("team", ProbeSupportStatus.SUPPORTED),
            _probe("removed", ProbeSupportStatus.SUPPORTED),
        ),
    )
    current = UpstreamProbeSuiteResult(
        suite_id="omx-basic",
        target="omx",
        results=(
            _probe("version", ProbeSupportStatus.SUPPORTED),
            _probe("team", ProbeSupportStatus.UNSUPPORTED),
            _probe("added", ProbeSupportStatus.SUPPORTED),
        ),
    )
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(fixture.model_dump_json(indent=2), encoding="utf-8")

    comparison = compare_probe_fixture(fixture_path, current)

    assert comparison.added_capabilities == ("added",)
    assert comparison.removed_capabilities == ("removed",)
    assert comparison.status_changes[0].capability == "team"
    assert comparison.status_changes[0].fixture_status == ProbeSupportStatus.SUPPORTED
    assert comparison.status_changes[0].current_status == ProbeSupportStatus.UNSUPPORTED
    assert comparison.matches is False
