from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class TuiCommandSectionLabel:
    """Human-facing command suite label for the TUI workbench."""

    group: str
    label: str
    warning: str | None = None


TUI_COMMAND_SECTION_LABELS: Final[dict[str, TuiCommandSectionLabel]] = {
    "route-next": TuiCommandSectionLabel(
        group="Lifecycle",
        label="Lifecycle → Route Next",
        warning="Route recommendation only; it does not mutate runtime state.",
    ),
    "discovery-gate": TuiCommandSectionLabel(
        group="Lifecycle",
        label="Lifecycle → Discovery Gate",
        warning=(
            "Clarification, ROI/no-build, and deep-interview handoff only; "
            "it does not implement."
        ),
    ),
    "research-brief": TuiCommandSectionLabel(
        group="Lifecycle",
        label="Lifecycle → Research Brief",
        warning="External/current research may be planned; verify sources before acting.",
    ),
    "idea-to-prd": TuiCommandSectionLabel(
        group="Lifecycle",
        label="Lifecycle → Idea to PRD",
        warning="Planning artifacts only; implementation starts at implementation-kickoff.",
    ),
    "implementation-kickoff": TuiCommandSectionLabel(
        group="Lifecycle",
        label="Lifecycle → Collaboration / Implementation Kickoff",
        warning="Runtime launch remains a policy-gated handoff.",
    ),
    "team-sync": TuiCommandSectionLabel(
        group="Lifecycle",
        label="Lifecycle → Team Sync",
        warning="Read-only Team evidence; suggested dispatches do not mutate mailboxes.",
    ),
    "integration-plan": TuiCommandSectionLabel(
        group="Lifecycle",
        label="Lifecycle → Integration Plan",
        warning="Planning only; it does not merge changes.",
    ),
    "review-gate": TuiCommandSectionLabel(
        group="Lifecycle",
        label="Lifecycle → Review Gate",
        warning="Approve/block review verdict; release closeout is separate.",
    ),
    "release-readiness": TuiCommandSectionLabel(
        group="Lifecycle",
        label="Lifecycle → Release Readiness",
        warning="May include docs, run ledger, and Alexandria MCP closeout guidance.",
    ),
    "company-run": TuiCommandSectionLabel(
        group="Macro",
        label="Macro → Company Run",
        warning="Macro orchestration with gates, voting, Team, subagents, and policy handoffs.",
    ),
    "adapter-ops mcp-audit": TuiCommandSectionLabel(
        group="Adapter Ops",
        label="Adapter Ops → MCP Audit",
        warning="Maintenance namespace; not a public lifecycle workflow.",
    ),
    "adapter-ops contract-refresh": TuiCommandSectionLabel(
        group="Adapter Ops",
        label="Adapter Ops → Contract Refresh",
        warning="Maintenance namespace; probe/fixture writes must be explicit.",
    ),
    "adapter-ops skillize": TuiCommandSectionLabel(
        group="Adapter Ops",
        label="Adapter Ops → Skillize",
        warning="Writes skill files only through explicit execution.",
    ),
    "adapter-ops run-ledger": TuiCommandSectionLabel(
        group="Adapter Ops",
        label="Adapter Ops → Run Ledger",
        warning="Read-only run record inspection by default.",
    ),
    "adapter-ops memory-capture": TuiCommandSectionLabel(
        group="Adapter Ops",
        label="Adapter Ops → Memory Capture",
        warning="Uses Alexandria MCP tools for curated memory capture; avoid secrets.",
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
