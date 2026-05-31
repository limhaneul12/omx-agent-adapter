from pathlib import Path

from omx_remote.runtime.agents.codex_agent_materialization_plan import (
    build_codex_agent_materialization_plan,
)
from omx_remote.runtime.agents.codex_agent_materializer import (
    apply_codex_agent_materialization,
    read_codex_agent_materialization_status,
)
from omx_remote.schemas.agents.codex_agent_materialization_schemas import (
    CodexAgentMaterializationTarget,
)
from tests.agents.test_codex_agent_materialization_plan import (
    _write_agent_config,
    _write_codex_contract,
)


def test_apply_codex_materialization_dry_run_does_not_write(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    _write_codex_contract(codex_home)
    _write_agent_config(tmp_path)
    plan = build_codex_agent_materialization_plan(tmp_path, codex_home=codex_home)

    result = apply_codex_agent_materialization(plan, dry_run=True)

    assert result.dry_run is True
    assert result.written_files == ()
    assert not Path(plan.files[0].target_path).exists()


def test_apply_codex_materialization_writes_and_status_matches(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    _write_codex_contract(codex_home)
    _write_agent_config(tmp_path)
    plan = build_codex_agent_materialization_plan(tmp_path, codex_home=codex_home)

    result = apply_codex_agent_materialization(plan, dry_run=False)
    status = read_codex_agent_materialization_status(tmp_path, codex_home=codex_home)

    assert result.dry_run is False
    assert result.written_files == (plan.files[0].target_path,)
    assert (
        Path(plan.files[0].target_path).read_text(encoding="utf-8")
        == plan.files[0].content
    )
    assert status.up_to_date is True
    assert status.target == CodexAgentMaterializationTarget.PROJECT
    assert status.files[0].matches is True


def test_apply_codex_materialization_writes_global_namespace(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    _write_codex_contract(codex_home)
    _write_agent_config(tmp_path)
    plan = build_codex_agent_materialization_plan(
        tmp_path,
        codex_home=codex_home,
        target=CodexAgentMaterializationTarget.GLOBAL,
        namespace="sample-project",
    )

    result = apply_codex_agent_materialization(plan, dry_run=False)
    status = read_codex_agent_materialization_status(
        tmp_path,
        codex_home=codex_home,
        target=CodexAgentMaterializationTarget.GLOBAL,
        namespace="sample-project",
    )

    assert result.written_files == (plan.files[0].target_path,)
    assert Path(plan.files[0].target_path).exists()
    assert status.target == CodexAgentMaterializationTarget.GLOBAL
    assert status.files[0].materialized_agent_name == "sample-project-architect"
    assert status.files[0].matches is True
