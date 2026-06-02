"""Constants shared by company-run discovery payload builders."""

_DISCOVERY_PERSPECTIVES: tuple[str, ...] = (
    "ceo/orchestrator",
    "product/pm",
    "technical/cto",
    "risk/security/critic",
)

_CHEAPER_ALTERNATIVES: tuple[str, ...] = (
    "route-next",
    "research-brief",
    "idea-to-prd",
    "implementation-kickoff",
)

_EXPECTED_COMPANY_ARTIFACTS: tuple[str, ...] = (
    "PRD",
    "test spec",
    "execution brief",
    "implementation-kickoff",
    "Team dispatch evidence",
    "review and release-readiness evidence",
)

