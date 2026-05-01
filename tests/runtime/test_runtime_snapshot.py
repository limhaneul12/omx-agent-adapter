from runtime import runtime_snapshot


class DummyResult:
    def __init__(self, stdout: str = "ok", stderr: str = "") -> None:
        self.stdout = stdout
        self.stderr = stderr


def test_read_runtime_status_uses_stdout(monkeypatch) -> None:
    monkeypatch.setattr(runtime_snapshot, "run_omx_command", lambda args: DummyResult(stdout="No active modes.\n"))

    assert runtime_snapshot.read_runtime_status() == "No active modes."
