from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalReviewPolicy
from omx_remote.schemas.codex_goal.supervisor_schemas import (
    GoalToRalphHandoffPromptRequest,
)


class GoalToRalphHandoffPromptRenderer:
    """Renders a Ralph PRD handoff prompt from one typed Goal request."""

    def __init__(self, request: GoalToRalphHandoffPromptRequest) -> None:
        """Initializes a prompt renderer for one Goal-to-Ralph handoff request.

        Args:
            request [GoalToRalphHandoffPromptRequest]: Typed Goal-to-Ralph handoff data.
        """
        self.request: GoalToRalphHandoffPromptRequest = request

    def _format_bullets(self, values: tuple[str, ...]) -> str:
        """Formats one tuple of prompt values as markdown bullets.

        Args:
            values [tuple[str, ...]]: Prompt values to render as bullet lines.

        Returns:
            str: Newline-delimited markdown bullet lines.
        """
        bullet_lines: list[str] = [f"- {value}" for value in values]
        formatted_bullets: str = "\n".join(bullet_lines)
        return formatted_bullets

    def _format_review_instruction(self) -> str:
        """Formats the review-policy-specific Ralph instruction.

        Returns:
            str: Review instruction line for the handoff prompt.
        """
        if self.request.review_policy == CodexGoalReviewPolicy.REVIEW_REQUIRED:
            review_instruction: str = (
                "Stop after creating or validating the PRD artifact and wait for review."
            )
            return review_instruction

        review_instruction = (
            "After creating or validating the PRD artifact, report whether the artifact is ready for the next supervised advance."
        )
        return review_instruction

    def _format_team_worker_count(self) -> str:
        """Formats the optional Team worker-count request.

        Returns:
            str: Team worker-count policy line for the handoff prompt.
        """
        if self.request.team_worker_count is None:
            formatted_worker_count: str = "team_worker_count: not requested"
            return formatted_worker_count

        formatted_worker_count = f"team_worker_count: {self.request.team_worker_count}"
        return formatted_worker_count

    def render(self) -> str:
        """Renders the full Ralph PRD handoff prompt.

        Returns:
            str: Prompt text Ralph can use to create or validate the PRD artifact.
        """
        source_path_lines: str = self._format_bullets(self.request.source_paths)
        constraint_lines: str = self._format_bullets(self.request.constraints)
        verification_lines: str = self._format_bullets(
            self.request.verification_expectations
        )
        review_instruction: str = self._format_review_instruction()
        team_worker_count_line: str = self._format_team_worker_count()

        prompt: str = f"""You are Ralph, the PRD and execution-structuring operator for this repo.

Goal ID: {self.request.goal_id}

Goal objective:
{self.request.goal_objective_text}

Requested slice:
{self.request.requested_slice}

Source of truth:
{source_path_lines}

Constraints:
{constraint_lines}

Verification expectations:
{verification_lines}

Task:
Create or validate `.omx/prd.json` as a RalphPrdArtifact for the requested slice only.

The RalphPrdArtifact must include:
- objective
- scope
- constraints
- execution_plan
- verification_expectations
- requires_team_fanout
- team_worker_count when Team fanout is required
- continuation_policy

Pipeline policy:
- Preserve Ralph and Team as independently operable modes.
- Do not implement code from this handoff prompt.
- Do not launch Team from this handoff prompt.
- {team_worker_count_line}
- {review_instruction}
""".strip()
        return prompt


def build_goal_to_ralph_handoff_prompt(
    request: GoalToRalphHandoffPromptRequest,
) -> str:
    """Render the Ralph PRD handoff prompt for a tracked Codex Goal.

    Args:
        request [GoalToRalphHandoffPromptRequest]: Typed Goal-to-Ralph handoff data.

    Returns:
        str: Prompt text Ralph can use to create or validate the PRD artifact.
    """
    renderer = GoalToRalphHandoffPromptRenderer(request)
    prompt: str = renderer.render()
    return prompt
