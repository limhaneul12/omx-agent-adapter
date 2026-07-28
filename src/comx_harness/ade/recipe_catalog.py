from __future__ import annotations

from pathlib import Path

from comx_harness.schemas.ade_operator_schemas import Recipe
from comx_harness.schemas.execution_schemas import ExecutionRequest, RunOptions
from comx_harness.shared.harness_enums.execution_enums import (
    ApprovalPolicy,
    SandboxMode,
)
from comx_harness.shared.harness_enums.operator_enums import RecipeId
from comx_harness.shared.harness_enums.provider_enums import ProviderId

_BUILTIN_RECIPES: tuple[Recipe, ...] = (
    Recipe(
        recipe_id=RecipeId.QUICK_REVIEW,
        title="Quick Review",
        description="Read-only evidence-backed repository review with Codex.",
        provider=ProviderId.CODEX,
    ),
    Recipe(
        recipe_id=RecipeId.IMPLEMENT_SAFELY,
        title="Implement Safely",
        description="Explicit workspace mutation with Codex and on-request approval.",
        provider=ProviderId.CODEX,
        mutation_allowed=True,
        sandbox=SandboxMode.WORKSPACE_WRITE,
        approval_policy=ApprovalPolicy.ON_REQUEST,
    ),
    Recipe(
        recipe_id=RecipeId.IMPLEMENT_AND_VERIFY,
        title="Implement and Verify",
        description="Codex mutation run that requires a result and verification artifact.",
        provider=ProviderId.CODEX,
        mutation_allowed=True,
        sandbox=SandboxMode.WORKSPACE_WRITE,
        approval_policy=ApprovalPolicy.ON_REQUEST,
        expected_artifacts=("verification.md",),
    ),
    Recipe(
        recipe_id=RecipeId.OMX_GOAL_EXECUTION,
        title="OMX Goal Execution",
        description="Use native OMX orchestration without recreating it in the adapter.",
        provider=ProviderId.OMX,
        mutation_allowed=True,
        sandbox=SandboxMode.WORKSPACE_WRITE,
        approval_policy=ApprovalPolicy.ON_REQUEST,
    ),
)


def builtin_recipes() -> tuple[Recipe, ...]:
    return _BUILTIN_RECIPES


def recipe_by_id(recipe_id: RecipeId | str) -> Recipe:
    resolved_id = RecipeId(recipe_id)
    for recipe in _BUILTIN_RECIPES:
        if recipe.recipe_id == resolved_id:
            return recipe
    raise ValueError(f"unsupported recipe: {resolved_id}")


def build_recipe_request(
    *,
    recipe: Recipe,
    objective: str,
    workspace: str | Path,
    controller_id: str = "human-operator",
) -> ExecutionRequest:
    request = ExecutionRequest(
        controller_id=controller_id,
        provider=recipe.provider,
        objective=objective,
        workspace=str(Path(workspace).resolve()),
        mutation_allowed=recipe.mutation_allowed,
        timeout_seconds=recipe.timeout_seconds,
        expected_artifacts=recipe.expected_artifacts,
        options=RunOptions(
            sandbox=recipe.sandbox,
            approval_policy=recipe.approval_policy,
            search=recipe.search,
            ephemeral=recipe.ephemeral,
        ),
    )
    return request
