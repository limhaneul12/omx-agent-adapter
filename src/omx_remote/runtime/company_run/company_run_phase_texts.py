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
