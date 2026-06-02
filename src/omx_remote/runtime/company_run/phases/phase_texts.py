def memory_recall_markdown(objective: str) -> str:
    """Render memory recall artifact text.

    Args:
        objective [str]: Company-run objective.

    Returns:
        str: Markdown artifact text.
    """
    text = f"""# Memory recall

Objective: {objective}

Concrete Alexandria MCP tool points:
- alexandria_search_vault: prior company-run decisions and project intent.
- alexandria_read_note: selected long-term memory notes.
- alexandria_get_current_memory_compact: compact recovery when available.
- alexandria_save_note: verified closeout only.

If these tools are unavailable in a runtime, record the limitation explicitly and continue from local artifacts.
"""
    return text


def discovery_summary_markdown(
    objective: str,
    verdict: str,
    recommended_next_command: str,
) -> str:
    """Render Gate 0 discovery summary text.

    Args:
        objective [str]: Company-run objective.
        verdict [str]: Discovery-gate verdict.
        recommended_next_command [str]: Recommended next command.

    Returns:
        str: Markdown artifact text.
    """
    text = f"""# Discovery gate summary

Objective: {objective}

Decision: {verdict}
Recommended next command: {recommended_next_command}

This Gate 0 summary records whether company-run is worth the orchestration cost before Research Council, PRD Council, Executive Council, Team, or scoped subagents spend tokens.
"""
    return text


def deep_interview_handoff_markdown(objective: str, invocation: str) -> str:
    """Render OMX deep-interview bridge handoff text.

    Args:
        objective [str]: Company-run objective.
        invocation [str]: Suggested OMX deep-interview invocation.

    Returns:
        str: Markdown artifact text.
    """
    text = f"""# Deep-interview handoff

Objective: {objective}

Suggested invocation:

```bash
{invocation}
```

Use this only when Gate 0 cannot settle non-goals, decision boundaries, acceptance criteria, or delegation authority. The handoff returns to discovery-gate before company-run continues.
"""
    return text


def user_facing_decision_report_markdown(
    decision: str,
    rationale: tuple[str, ...],
    concerns: tuple[str, ...],
    next_actions: tuple[str, ...],
    artifact_paths: tuple[str, ...],
) -> str:
    """Render a user-facing company-run decision report.

    Args:
        decision [str]: User-visible decision.
        rationale [tuple[str, ...]]: Decision rationale bullets.
        concerns [tuple[str, ...]]: Concern bullets.
        next_actions [tuple[str, ...]]: Next-action bullets.
        artifact_paths [tuple[str, ...]]: Artifact references.

    Returns:
        str: Markdown artifact text.
    """
    rationale_text = "\n".join(f"- {item}" for item in rationale)
    concerns_text = "\n".join(f"- {item}" for item in concerns)
    next_actions_text = "\n".join(f"- {item}" for item in next_actions)
    artifact_text = "\n".join(f"- {path}" for path in artifact_paths)
    text = f"""# Company-run decision report

Decision: {decision}

## Rationale

{rationale_text}

## Concerns

{concerns_text}

## Next actions

{next_actions_text}

## Artifact paths

{artifact_text}

Governance details are persisted as internal artifacts and are available for audit when requested, but the default user surface is this decision report rather than raw ballot ceremony.
"""
    return text


def prd_markdown(objective: str) -> str:
    """Render PRD artifact text.

    Args:
        objective [str]: Company-run objective.

    Returns:
        str: Markdown artifact text.
    """
    text = f"""# PRD

## Objective

{objective}

## Non-negotiables

- Team and subagents are required.
- No implementation before PRD/test spec/execution brief.
- Votes and review gates are recorded.
"""
    return text


def test_spec_markdown(objective: str) -> str:
    """Render test specification artifact text.

    Args:
        objective [str]: Company-run objective.

    Returns:
        str: Markdown artifact text.
    """
    text = f"""# Test spec

Objective: {objective}

- Verify roster guard.
- Verify phase gates.
- Verify MCP status/artifacts.
- Verify dogfood leaves only run artifacts.
"""
    return text


def execution_brief_markdown(objective: str) -> str:
    """Render execution brief artifact text.

    Args:
        objective [str]: Company-run objective.

    Returns:
        str: Markdown artifact text.
    """
    text = f"""# Execution brief

Objective: {objective}

Use implementation-kickoff to start OMX Team only after planning artifacts and executive readiness exist.
"""
    return text


def risks_markdown() -> str:
    """Render risks and decisions artifact text.

    Returns:
        str: Markdown artifact text.
    """
    text = "# Risks and decisions\n\n- Do not fabricate Team completion.\n- Stop if product mutation is unsafe.\n- Preserve Alexandria memory closeout.\n"
    return text


def kickoff_markdown(objective: str) -> str:
    """Render implementation-kickoff artifact text.

    Args:
        objective [str]: Company-run objective.

    Returns:
        str: Markdown artifact text.
    """
    text = f"""# Implementation kickoff

Objective: {objective}

Development starts here, after PRD/test spec/execution brief and executive readiness.
"""
    return text
