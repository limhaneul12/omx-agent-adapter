import orjson

from omx_remote.runtime.company_run.company_run_council_runtime import (
    final_agent_message_from_codex_stdout,
    recover_output_last_message_from_stdout,
)


def test_final_agent_message_from_codex_stdout_returns_last_agent_message() -> None:
    stdout = "\n".join(
        (
            orjson.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "first"},
                }
            ).decode(),
            orjson.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution",
                        "aggregated_output": "ignore",
                    },
                }
            ).decode(),
            orjson.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "# Risk\n\nfinal"},
                }
            ).decode(),
        )
    )

    message = final_agent_message_from_codex_stdout(stdout=stdout)

    assert message == "# Risk\n\nfinal"


def test_recover_output_last_message_from_stdout_writes_artifact(tmp_path) -> None:
    output_path = tmp_path / "risk-security.md"
    stdout = orjson.dumps(
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "# Risk\n\nfinal"},
        }
    ).decode()

    recovered = recover_output_last_message_from_stdout(
        output_path=output_path,
        stdout=stdout,
    )

    assert recovered is True
    assert output_path.read_text(encoding="utf-8") == "# Risk\n\nfinal"
