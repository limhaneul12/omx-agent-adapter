from omx_remote.runtime.prompt_assets import render_prompt_model_asset
from omx_remote.schemas.codex_goal.runtime_schemas import CodexGoalReviewPolicy
from omx_remote.schemas.codex_goal.supervisor_schemas import (
    GoalPrdAuthoringPromptContext,
    GoalPrdAuthoringPromptRequest,
)


class GoalPrdAuthoringPromptRenderer:
    """Renders a Goal-scoped PRD authoring prompt from one typed Goal request."""

    def __init__(self, request: GoalPrdAuthoringPromptRequest) -> None:
        """Initializes a prompt renderer for one Goal-scoped PRD request.

        Args:
            request [GoalPrdAuthoringPromptRequest]: Typed Goal PRD authoring data.
        """
        self.request: GoalPrdAuthoringPromptRequest = request

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

    def _format_constraint_bullets(self) -> str:
        """Formats handoff constraints, including the explicit empty-constraints state.

        Returns:
            str: Markdown bullet lines for handoff constraints.
        """
        if not self.request.constraints:
            empty_constraint_lines: str = (
                "- No additional handoff constraints supplied."
            )
            return empty_constraint_lines

        constraint_lines: str = self._format_bullets(self.request.constraints)
        return constraint_lines

    def _format_review_instruction(self) -> str:
        """Formats the review-policy-specific PRD authoring instruction.

        Returns:
            str: Review instruction line for the handoff prompt.
        """
        if self.request.review_policy == CodexGoalReviewPolicy.REVIEW_REQUIRED:
            review_instruction: str = (
                "Stop after producing the PRD JSON artifact and wait for review."
            )
            return review_instruction

        review_instruction = "After producing the PRD JSON artifact, report whether it is ready for `comx-agent prd validate`."
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
        """Renders the full Goal-scoped PRD authoring prompt.

        Returns:
            str: Prompt text a Goal-scoped authoring agent can use to produce PRD JSON.
        """
        source_path_lines: str = self._format_bullets(self.request.source_paths)
        constraint_lines: str = self._format_constraint_bullets()
        verification_lines: str = self._format_bullets(
            self.request.verification_expectations
        )
        review_instruction: str = self._format_review_instruction()
        team_worker_count_line: str = self._format_team_worker_count()

        prompt_context = GoalPrdAuthoringPromptContext(
            goal_id=self.request.goal_id,
            goal_objective_text=self.request.goal_objective_text,
            requested_slice=self.request.requested_slice,
            source_path_lines=source_path_lines,
            constraint_lines=constraint_lines,
            verification_lines=verification_lines,
            team_worker_count_line=team_worker_count_line,
            review_instruction=review_instruction,
        )
        prompt: str = render_prompt_model_asset(
            parts=("goal", "prd-authoring.md"),
            replacements=prompt_context,
        )
        return prompt


def build_goal_prd_authoring_prompt(
    request: GoalPrdAuthoringPromptRequest,
) -> str:
    """Render the Goal-scoped PRD authoring prompt for a tracked Codex Goal.

    Args:
        request [GoalPrdAuthoringPromptRequest]: Typed Goal-scoped PRD data.

    Returns:
        str: Prompt text a Goal-scoped authoring agent can use to produce PRD JSON.
    """
    renderer = GoalPrdAuthoringPromptRenderer(request)
    prompt: str = renderer.render()
    return prompt
