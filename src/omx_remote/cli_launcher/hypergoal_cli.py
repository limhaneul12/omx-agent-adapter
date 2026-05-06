import typer

HYPERGOAL_TEMPLATE_TEXT = """# Hypergoal Deep-Work Scaffold

Hypergoal:
  <Large objective that needs Goal-level done conditions plus Ultrawork-style focus/resume context.>

Context to preserve:
  <Files, prior decisions, current state, risks, and handoff facts the agent must not lose.>

Focus window:
  <Expected deep-work span, checkpoints, and when to stop for review.>

Constraints:
  <Non-goals, safety limits, no automatic fanout/merge/close, and project rules.>

Done When:
  <Concrete completion criteria, verification commands, and required handoff notes.>

Recovery checklist:
  - Record what changed and what remains.
  - Keep enough context for another agent to resume.
  - Verify before continuing to the next deep-work checkpoint.
  - Stop instead of guessing when context is missing.
"""

hypergoal_app = typer.Typer(
    help="Print lightweight Hypergoal deep-work scaffolds.",
    add_completion=False,
)


@hypergoal_app.command("template", help="Print a static Hypergoal deep-work scaffold.")
def hypergoal_template() -> None:
    """Print a static Hypergoal deep-work scaffold."""
    typer.echo(HYPERGOAL_TEMPLATE_TEXT)
