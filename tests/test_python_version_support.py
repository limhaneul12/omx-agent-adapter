from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict[str, object]:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_project_declares_python_313_and_314_support() -> None:
    pyproject = _pyproject()
    project = pyproject["project"]

    assert project["requires-python"] == ">=3.13,<3.15"


def test_static_tools_keep_python_313_as_lower_bound_compatibility_gate() -> None:
    pyproject = _pyproject()
    tool = pyproject["tool"]
    ruff = tool["ruff"]
    pyrefly = tool["pyrefly"]

    assert ruff["target-version"] == "py313"
    assert pyrefly["python-version"] == "3.13"


def test_lockfile_does_not_pin_runtime_to_python_313_only() -> None:
    lockfile_text = (ROOT / "uv.lock").read_text()

    assert 'requires-python = ">=3.13, <3.15"' in lockfile_text
    assert 'requires-python = "==3.13.*"' not in lockfile_text


def test_codebase_avoids_python_314_removed_or_misstated_typing_surfaces() -> None:
    source_paths = [
        *Path(ROOT, "src").rglob("*.py"),
    ]
    source_text = "\n".join(path.read_text() for path in source_paths)

    assert "typing.ByteString" not in source_text
    assert "from typing import ByteString" not in source_text
    assert "typing.TypeForm" not in source_text
    assert "from typing import TypeForm" not in source_text
