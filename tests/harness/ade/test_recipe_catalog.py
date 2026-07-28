from pathlib import Path

from comx_harness.ade.recipe_catalog import (
    build_recipe_request,
    builtin_recipes,
    recipe_by_id,
)
from comx_harness.shared.harness_enums.execution_enums import SandboxMode
from comx_harness.shared.harness_enums.operator_enums import RecipeId
from comx_harness.shared.harness_enums.provider_enums import ProviderId


def test_builtin_recipes_are_small_and_unique() -> None:
    recipes = builtin_recipes()

    assert len(recipes) == 4
    assert len({recipe.recipe_id for recipe in recipes}) == len(recipes)


def test_quick_review_maps_to_read_only_request(tmp_path: Path) -> None:
    request = build_recipe_request(
        recipe=recipe_by_id(RecipeId.QUICK_REVIEW),
        objective="Review the repository.",
        workspace=tmp_path,
    )

    assert request.provider == ProviderId.CODEX
    assert request.mutation_allowed is False
    assert request.options.sandbox == SandboxMode.READ_ONLY
    assert request.workspace == str(tmp_path.resolve())
    assert request.controller_id == "human-operator"


def test_omx_goal_maps_to_explicit_workspace_mutation(tmp_path: Path) -> None:
    request = build_recipe_request(
        recipe=recipe_by_id(RecipeId.OMX_GOAL_EXECUTION),
        objective="Complete the goal using native OMX.",
        workspace=tmp_path,
    )

    assert request.provider == ProviderId.OMX
    assert request.mutation_allowed is True
    assert request.options.sandbox == SandboxMode.WORKSPACE_WRITE
