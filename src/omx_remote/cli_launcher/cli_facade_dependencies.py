"""Top-level CLI dependency seams shared by launcher modules."""

from omx_remote.execution.invoke import run_omx_command, run_omx_command_inherited_stdio
from omx_remote.runtime.status.runtime_mode_state import read_runtime_mode_state
from omx_remote.runtime.status.runtime_mode_status import read_runtime_mode_status

__all__ = (
    "read_runtime_mode_state",
    "read_runtime_mode_status",
    "run_omx_command",
    "run_omx_command_inherited_stdio",
)
