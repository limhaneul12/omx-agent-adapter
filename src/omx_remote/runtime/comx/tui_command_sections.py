from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class TuiCommandSectionLabel:
    """Human-facing command suite label for the TUI workbench."""

    group: str
    label: str
    warning: str | None = None


TUI_COMMAND_SECTION_LABELS: Final[dict[str, TuiCommandSectionLabel]] = {
    "collaboration-kickoff": TuiCommandSectionLabel(
        group="Collaboration",
        label="Collaboration → Kickoff",
        warning="Team/UltraGoal launch remains a policy-gated handoff.",
    ),
    "team-standup-sync": TuiCommandSectionLabel(
        group="Collaboration",
        label="Collaboration → Team Standup Sync",
        warning="Read-only Team evidence; suggested dispatches do not mutate mailboxes.",
    ),
    "integration-room": TuiCommandSectionLabel(
        group="Collaboration",
        label="Collaboration → Integration Room",
        warning="Integration changes require a separate explicit implementation command.",
    ),
    "conflict-resolution-council": TuiCommandSectionLabel(
        group="Collaboration",
        label="Collaboration → Conflict Resolution Council",
        warning="Decision record only; it does not apply patches.",
    ),
    "parallel-review-board": TuiCommandSectionLabel(
        group="Review",
        label="Review → Parallel Review Board",
        warning="Review lanes are read-only and must cite evidence.",
    ),
    "release-readiness-room": TuiCommandSectionLabel(
        group="Release",
        label="Release → Release Readiness Room",
        warning="Alexandria closeout writes summary-only memory; no secrets.",
    ),
    "idea-to-prd-council": TuiCommandSectionLabel(
        group="Research",
        label="Research → Idea to PRD Council",
        warning="Starts/ends with Alexandria and hands off UltraGoal only after agent validation.",
    ),
}


def command_section_label(command_id: str) -> TuiCommandSectionLabel | None:
    """Return the TUI section label for one command id.

    Args:
        command_id: See function signature.

    Returns:
        See function return annotation.
    """
    section_label: TuiCommandSectionLabel | None = TUI_COMMAND_SECTION_LABELS.get(
        command_id
    )
    return section_label
