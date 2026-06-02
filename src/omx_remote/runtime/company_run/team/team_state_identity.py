import re
from pathlib import Path

_TEAM_NAME_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"active team exists\s*\(\s*([A-Za-z0-9_.-]+)\s*\)",
        re.IGNORECASE,
    ),
    re.compile(r'"team_name"\s*:\s*"([A-Za-z0-9_.-]+)"', re.IGNORECASE),
    re.compile(r"team(?: name)?[:=]\s*([A-Za-z0-9_.-]+)", re.IGNORECASE),
    re.compile(r"omx team status\s+([A-Za-z0-9_.-]+)", re.IGNORECASE),
    re.compile(
        r"team\s+([A-Za-z0-9_.-]+)\s+(?:created|started|launched)", re.IGNORECASE
    ),
)
_MISSING_TEAM_NAME_SENTINELS: frozenset[str] = frozenset({"missing-team"})


def team_name_from_output(output: str) -> str | None:
    """Extract a likely OMX Team name from launch output.

    Args:
        output [str]: Captured launch stdout/stderr.

    Returns:
        str | None: Team name when detected.
    """
    for pattern in _TEAM_NAME_PATTERNS:
        match = pattern.search(output)
        if match is not None:
            team_name = match.group(1)
            return team_name
    missing_name: None = None
    return missing_name


def team_name_from_launch_evidence(cwd: Path, output: str) -> str | None:
    """Resolve the actionable Team name from launch output plus local state.

    Args:
        cwd [Path]: Repository root that native OMX Team operated on.
        output [str]: Combined launch stdout/stderr evidence.

    Returns:
        str | None: Concrete Team name when available.
    """
    output_team_name = team_name_from_output(output)
    state_team_name = latest_team_state_name(cwd=cwd)
    if _usable_team_name(output_team_name):
        resolved_name = output_team_name
        return resolved_name
    if state_team_name is not None:
        resolved_name = state_team_name
        return resolved_name
    missing_name: None = None
    return missing_name


def latest_team_state_name(cwd: Path) -> str | None:
    """Return the newest native OMX Team state directory name.

    Args:
        cwd [Path]: Repository root that native OMX Team operated on.

    Returns:
        str | None: Team name from the newest state directory when available.
    """
    team_state_root = cwd / ".omx" / "state" / "team"
    if not team_state_root.is_dir():
        missing_name: None = None
        return missing_name
    team_dirs = tuple(
        path
        for path in team_state_root.iterdir()
        if path.is_dir() and _usable_team_name(path.name)
    )
    if not team_dirs:
        missing_name = None
        return missing_name
    latest_team_dir = max(team_dirs, key=lambda path: path.stat().st_mtime)
    team_name = latest_team_dir.name
    return team_name


def _usable_team_name(team_name: str | None) -> bool:
    """Return whether a candidate Team name is an actionable native Team id.

    Args:
        team_name [str | None]: Candidate Team name.

    Returns:
        bool: True for concrete names, false for known missing placeholders.
    """
    usable = team_name is not None and team_name not in _MISSING_TEAM_NAME_SENTINELS
    return usable


def team_state_evidence_text(cwd: Path, team_name: str | None) -> str:
    """Read bounded native Team startup/status evidence as text.

    Args:
        cwd [Path]: Repository root that native OMX Team operated on.
        team_name [str | None]: Team state directory name.

    Returns:
        str: Bounded state evidence text.
    """
    if team_name is None:
        missing_text = ""
        return missing_text
    team_state_dir = cwd / ".omx" / "state" / "team" / team_name
    evidence_paths = (
        team_state_dir / "phase.json",
        team_state_dir / "startup-timing.json",
        team_state_dir / "events" / "events.ndjson",
        *tuple((team_state_dir / "workers").glob("*/status.json")),
    )
    evidence_parts = [
        evidence_path.read_text(encoding="utf-8")[:20_000]
        for evidence_path in evidence_paths
        if evidence_path.is_file()
    ]
    evidence_text = "\n".join(evidence_parts)
    return evidence_text


