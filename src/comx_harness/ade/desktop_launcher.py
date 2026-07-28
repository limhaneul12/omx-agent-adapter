from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

_TK_PROBE = (
    "import sys, tkinter as tk; "
    "assert sys.version_info[:2] == "
    f"{sys.version_info[:2]!r}; "
    "root = tk.Tk(); root.withdraw(); root.destroy()"
)


def launch_desktop_ade(workspace: str | Path) -> None:
    """Launch the ADE with a Python interpreter that has working Tk support."""
    resolved_workspace = Path(workspace).expanduser().resolve()
    # The virtual-environment symlink location participates in Tcl discovery,
    # so resolving it can produce a false-positive probe for the base runtime.
    current_interpreter = Path(sys.executable).absolute()
    candidate = _tk_interpreter(current_interpreter)
    if candidate is None and _current_tk_is_usable():
        _run_ade_in_current_interpreter(resolved_workspace)
        return
    if candidate is None:
        raise RuntimeError(
            "the ADE requires a Python 3.13 interpreter with usable Tk support"
        )
    command = (
        str(candidate),
        "-c",
        (
            "import sys; "
            "from comx_harness.ade.tk_app import run_ade; "
            "run_ade(sys.argv[1])"
        ),
        str(resolved_workspace),
    )
    environment = _bridge_environment()
    os.execve(candidate, command, environment)


def _current_tk_is_usable() -> bool:
    # Tk is optional for machine-facing commands, so importing it remains
    # localized to the desktop-launch boundary.
    try:
        import tkinter as tk
    except ImportError:
        return False
    try:
        root = tk.Tk()
        root.withdraw()
        root.destroy()
    except tk.TclError:
        return False
    return True


def _tk_interpreter(current_interpreter: Path) -> Path | None:
    candidates = (
        Path("/usr/local/bin/python3"),
        Path(
            "/Library/Frameworks/Python.framework/"
            f"Versions/{sys.version_info.major}.{sys.version_info.minor}/bin/python3"
        ),
        Path(shutil.which("python3") or current_interpreter),
    )
    for candidate in candidates:
        resolved_candidate = candidate.expanduser().absolute()
        if (
            resolved_candidate != current_interpreter
            and resolved_candidate.exists()
            and _tk_is_usable(resolved_candidate)
        ):
            return resolved_candidate
    return None


def _tk_is_usable(interpreter: Path) -> bool:
    completed = subprocess.run(
        (str(interpreter), "-c", _TK_PROBE),
        check=False,
        capture_output=True,
        timeout=10,
    )
    return completed.returncode == 0


def _bridge_environment() -> dict[str, str]:
    environment = os.environ.copy()
    import_paths = tuple(str(Path(entry).resolve()) for entry in sys.path if entry)
    existing_pythonpath = environment.get("PYTHONPATH")
    if existing_pythonpath:
        import_paths = (*import_paths, existing_pythonpath)
    # The candidate provides Tk; dependencies remain owned by the invoking
    # comx-agent installation instead of a second separately installed app.
    environment["PYTHONPATH"] = os.pathsep.join(import_paths)
    return environment


def _run_ade_in_current_interpreter(workspace: Path) -> None:
    # Delay Tk imports so every non-ADE CLI operation remains usable on
    # Python distributions that intentionally omit a desktop runtime.
    from comx_harness.ade.tk_app import run_ade

    run_ade(workspace)
