from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict[str, object]:
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_wheel_build_does_not_force_include_packaged_source_tree() -> None:
    pyproject = _pyproject()
    tool = pyproject["tool"]
    hatch = tool["hatch"]
    build = hatch["build"]
    targets = build["targets"]
    wheel = targets["wheel"]

    packages = wheel["packages"]
    force_include = wheel.get("force-include", {})

    assert "src/omx_remote" in packages
    assert force_include.get("src/omx_remote") is None


def test_readme_documents_private_install_before_public_pypi() -> None:
    readme = (ROOT / "README.md").read_text()

    assert "Install from GitHub" in readme
    assert "uv tool install git+https://github.com/limhaneul12/omx-agent-adapter.git" in readme
    assert "PyPI" in readme
    assert "not published" in readme
