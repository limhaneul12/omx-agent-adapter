import orjson
from typer.testing import CliRunner

import omx_remote.cli_launcher.probes_cli as probes_cli
from omx_remote.cli import app
from omx_remote.schemas.probes.upstream_probe_schemas import ProbeProcessOutput


def test_probes_run_cli_uses_injected_runner(monkeypatch) -> None:
    def fake_runner(command: tuple[str, ...]) -> ProbeProcessOutput:
        if command == ("omx", "--version"):
            return ProbeProcessOutput(exit_code=0, stdout="omx 0.18.0\n", stderr="")
        return ProbeProcessOutput(exit_code=1, stdout="", stderr="missing")

    monkeypatch.setattr(probes_cli, "run_probe_command", fake_runner)

    result = CliRunner().invoke(app, ["probes", "run", "omx-basic", "--json"])

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert payload["suite_id"] == "omx-basic"
    assert payload["results"][0]["capability"] == "version"


def test_probes_list_fixtures_cli_outputs_json() -> None:
    result = CliRunner().invoke(app, ["probes", "list-fixtures", "--json"])

    assert result.exit_code == 0
    payload = orjson.loads(result.stdout)
    assert "fixtures" in payload
