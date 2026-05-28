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


def test_comx_agent_console_script_preserves_agent_remote_alias() -> None:
    pyproject = _pyproject()
    scripts = pyproject["project"]["scripts"]

    assert scripts["agent-remote"] == "omx_agent_adapter_cli:app"
    assert scripts["comx-agent"] == "omx_agent_adapter_cli:app"


def test_readme_documents_private_install_before_public_pypi() -> None:
    readme = (ROOT / "README.md").read_text()

    assert "Install from GitHub" in readme
    assert "uv tool install git+https://github.com/limhaneul12/omx-agent-adapter.git" in readme
    assert "PyPI" in readme
    assert "not published" in readme


def test_readme_separates_installed_cli_from_development_uv_run() -> None:
    readme = (ROOT / "README.md").read_text()

    assert "After install, do not prefix normal CLI usage with `uv run`." in readme
    assert "agent-remote goal operating-decision" in readme
    assert "Use `uv run` only inside a checked-out development repository" in readme
