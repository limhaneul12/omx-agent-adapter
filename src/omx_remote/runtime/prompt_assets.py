from collections.abc import Mapping
from pathlib import Path

from pydantic import BaseModel

from omx_remote.shared.utils.json_model_dump import model_json_object


def _prompt_root() -> Path:
    """Return the installed or repo-local prompt directory.

    Returns:
        Path: Directory containing reusable prompt Markdown assets.
    """
    module_path = Path(__file__).resolve()
    candidate_roots = (
        module_path.parents[3],
        module_path.parents[2],
    )
    for root in candidate_roots:
        candidate = root / "prompt"
        if candidate.exists():
            return candidate
    fallback = module_path.parents[3] / "prompt"
    return fallback


def prompt_asset_path(*parts: str) -> str:
    """Return an absolute path to a repository prompt asset.

    Args:
        *parts [str]: Path segments under the prompt directory.

    Returns:
        str: Absolute prompt asset path.
    """
    asset_path = _prompt_root() / Path(*parts)
    prompt_path: str = str(asset_path)
    return prompt_path


def load_prompt_asset(*parts: str) -> str:
    """Read a reusable prompt asset as UTF-8 text.

    Args:
        *parts [str]: Path segments under the prompt directory.

    Returns:
        str: Prompt Markdown text without trailing whitespace.
    """
    prompt_path = Path(prompt_asset_path(*parts))
    prompt_text: str = prompt_path.read_text(encoding="utf-8").strip()
    return prompt_text


def render_prompt_asset(parts: tuple[str, ...], replacements: Mapping[str, str]) -> str:
    """Render a prompt asset by replacing double-brace placeholders.

    Args:
        parts [tuple[str, ...]]: Path segments under the prompt directory.
        replacements [Mapping[str, str]]: Placeholder names and rendered values.

    Returns:
        str: Rendered prompt text.
    """
    prompt_text = load_prompt_asset(*parts)
    for key, value in replacements.items():
        prompt_text = prompt_text.replace(f"{{{{{key}}}}}", value)
    return prompt_text


def render_prompt_model_asset(parts: tuple[str, ...], replacements: BaseModel) -> str:
    """Render a prompt asset from a Pydantic string-field context model.

    Args:
        parts [tuple[str, ...]]: Path segments under the prompt directory.
        replacements [BaseModel]: Pydantic replacement context with string values.

    Returns:
        str: Rendered prompt text.
    """
    raw_payload = model_json_object(replacements)
    replacement_items: dict[str, str] = {}
    for key, value in raw_payload.items():
        if not isinstance(value, str):
            raise ValueError(f"prompt replacement {key} is not a string")
        replacement_items[key] = value
    prompt_text = render_prompt_asset(parts=parts, replacements=replacement_items)
    return prompt_text
