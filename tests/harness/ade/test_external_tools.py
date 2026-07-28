from __future__ import annotations

from pathlib import Path

from comx_harness.ade.external_tools import ExternalToolService


class _FakeProcess:
    pid = 4321


def test_macos_targets_are_safe_argv_and_launch_without_shell(
    tmp_path: Path,
) -> None:
    calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def launcher(
        argv: tuple[str, ...],
        **kwargs: object,
    ) -> _FakeProcess:
        calls.append((argv, kwargs))
        return _FakeProcess()

    source = tmp_path / "file with spaces.py"
    source.write_text("pass\n", encoding="utf-8")
    service = ExternalToolService(platform="darwin", launcher=launcher)

    finder = service.finder_target(source)
    editor = service.editor_target(source, application="Visual Studio Code")
    terminal = service.terminal_target(source)
    launched = service.launch(editor)

    assert finder.argv == ("open", "-R", str(source))
    assert editor.argv == (
        "open",
        "-a",
        "Visual Studio Code",
        str(source),
    )
    assert terminal.argv == ("open", "-a", "Terminal", str(tmp_path))
    assert launched.launched is True
    assert launched.pid == 4321
    assert calls[0][0] == editor.argv
    assert "shell" not in calls[0][1]
    assert calls[0][1]["start_new_session"] is True


def test_unsupported_platform_and_missing_path_are_honest(tmp_path: Path) -> None:
    service = ExternalToolService(platform="linux")

    unsupported = service.finder_target(tmp_path)
    missing = service.terminal_target(tmp_path / "missing")

    assert unsupported.supported is False
    assert unsupported.argv == ()
    assert unsupported.message == "Finder is unsupported on platform linux"
    assert missing.supported is False
    assert missing.message == "target path does not exist"


def test_tmux_attach_requires_explicit_identity_and_preserves_evidence() -> None:
    service = ExternalToolService(platform="darwin")

    unknown = service.tmux_attach_target(None)
    observed = service.tmux_attach_target("omx-team-alpha")

    assert unknown.supported is False
    assert "explicit observed session identity" in (unknown.message or "")
    assert observed.argv == (
        "tmux",
        "attach-session",
        "-t",
        "omx-team-alpha",
    )
    assert "omx-team-alpha" in observed.evidence
