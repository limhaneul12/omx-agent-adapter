from pathlib import Path

from omx_remote.schemas.company_run.company_run_core_schemas import (
    CompanyRunArtifactIndex,
)

REQUIRED_COMPANY_RUN_ARTIFACTS: tuple[str, ...] = (
    "state.json",
    "roster.json",
    "phase-log.jsonl",
    "memory-recall.md",
    "discovery/discovery-decision-packet.json",
    "discovery/discovery-summary.md",
    "discovery/roi-no-build-gate.json",
    "discovery/deep-interview-handoff.md",
    "decisions/discovery-decision-report.json",
    "decisions/discovery-decision-report.md",
    "route-next.json",
    "research/domain-research.md",
    "research/technical-feasibility.md",
    "research/risk-security.md",
    "research/critic.md",
    "research/research-vote.json",
    "decisions/proceed-vote.json",
    "decisions/orchestrator-decision.md",
    "planning/prd.md",
    "planning/test-spec.md",
    "planning/execution-brief.md",
    "planning/risks-and-decisions.md",
    "planning/readiness-verdict.json",
    "executive/cto-review.md",
    "executive/ciso-security-review.md",
    "executive/qa-review.md",
    "executive/release-manager-review.md",
    "executive/executive-gate.json",
    "implementation/implementation-kickoff.md",
    "implementation/team-plan.json",
    "implementation/team-launch.json",
    "team/team-sync.md",
    "team/worker-dispatches.json",
    "team/integration-plan.md",
    "review/review-gate.json",
    "review/code-review.md",
    "review/security-review.md",
    "review/architecture-review.md",
    "review/qa-verdict.md",
    "release/release-readiness.json",
    "release/release-summary.md",
    "memory-closeout.md",
)


def company_run_artifact_root(run_dir: str | Path) -> Path:
    """Return the company-run artifact root for one run directory.

    Args:
        run_dir [str | Path]: Actual run directory.

    Returns:
        Path: Company-run artifact root.
    """
    root = Path(run_dir) / "company-run"
    return root


def build_company_run_artifact_index(run_dir: str | Path) -> CompanyRunArtifactIndex:
    """Build the required company-run artifact index for a run directory.

    Args:
        run_dir [str | Path]: Actual run directory.

    Returns:
        CompanyRunArtifactIndex: Required artifact path contract.
    """
    root = company_run_artifact_root(run_dir)
    paths: tuple[str, ...] = tuple(
        str(root / relative) for relative in REQUIRED_COMPANY_RUN_ARTIFACTS
    )
    index = CompanyRunArtifactIndex(
        run_id=Path(run_dir).name,
        root_path=str(root),
        artifact_paths=paths,
        artifacts=(),
    )
    return index
