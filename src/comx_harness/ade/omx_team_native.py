from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import orjson
from comx_harness.ade.omx_team_discovery import (
    discover_omx_team_names,
    validate_omx_team_name,
)
from comx_harness.ade.omx_team_projection import (
    project_omx_team,
    unavailable_omx_team,
)
from comx_harness.schemas.lifecycle_schemas import EventReport
from comx_harness.schemas.omx_team_schemas import (
    OmxConfigEnvelope,
    OmxMonitorEnvelope,
    OmxNativeMonitorSnapshot,
    OmxNativeTask,
    OmxNativeTeamConfig,
    OmxNativeTeamSummary,
    OmxSummaryEnvelope,
    OmxTasksEnvelope,
    OmxTeamProjection,
    OmxTeamStatusEnvelope,
)


@dataclass(frozen=True, slots=True)
class NativeCommandResult:
    return_code: int
    stdout: str
    stderr: str


NativeCommandRunner = Callable[[tuple[str, ...], Path], NativeCommandResult]


class OmxTeamObserver:
    """Read OMX Team state only through the installed native JSON CLI."""

    def __init__(
        self,
        workspace: str | Path,
        *,
        runner: NativeCommandRunner | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.runner = runner or _run_native_command

    def discover(self, events: EventReport) -> tuple[str, ...]:
        return discover_omx_team_names(events)

    def read(self, team_name: str) -> OmxTeamProjection:
        normalized = validate_omx_team_name(team_name)
        if shutil.which("omx") is None:
            return unavailable_omx_team(normalized, "OMX binary is unavailable.")
        try:
            status = OmxTeamStatusEnvelope.model_validate(
                self._json(("omx", "team", "status", normalized, "--json"))
            )
            if status.status == "missing":
                return unavailable_omx_team(
                    normalized,
                    "Native OMX reports that the team is missing.",
                )
            config = self._config(normalized)
            if config is None:
                return unavailable_omx_team(
                    normalized,
                    "Native OMX team config is unavailable.",
                )
            return project_omx_team(
                status=status.status,
                config=config,
                tasks=self._tasks(normalized),
                summary=self._summary(normalized),
                monitor=self._monitor(normalized),
            )
        except (OSError, ValueError) as error:
            return unavailable_omx_team(
                normalized,
                f"Native OMX team observation failed: {error}",
            )

    def _config(self, team_name: str) -> OmxNativeTeamConfig | None:
        envelope = OmxConfigEnvelope.model_validate(self._api("read-config", team_name))
        return envelope.data.config if envelope.ok and envelope.data else None

    def _tasks(self, team_name: str) -> tuple[OmxNativeTask, ...]:
        envelope = OmxTasksEnvelope.model_validate(self._api("list-tasks", team_name))
        return envelope.data.tasks if envelope.ok and envelope.data else ()

    def _summary(self, team_name: str) -> OmxNativeTeamSummary | None:
        envelope = OmxSummaryEnvelope.model_validate(
            self._api("get-summary", team_name)
        )
        return envelope.data.summary if envelope.ok and envelope.data else None

    def _monitor(self, team_name: str) -> OmxNativeMonitorSnapshot | None:
        envelope = OmxMonitorEnvelope.model_validate(
            self._api("read-monitor-snapshot", team_name)
        )
        return envelope.data.snapshot if envelope.ok and envelope.data else None

    def _api(self, operation: str, team_name: str) -> object:
        payload = orjson.dumps({"team_name": team_name}).decode("utf-8")
        return self._json(
            ("omx", "team", "api", operation, "--input", payload, "--json")
        )

    def _json(self, argv: tuple[str, ...]) -> object:
        result = self.runner(argv, self.workspace)
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if result.return_code != 0 or not lines:
            detail = result.stderr.strip() or "native command returned no JSON"
            raise ValueError(detail)
        try:
            return orjson.loads(lines[-1])
        except orjson.JSONDecodeError as error:
            raise ValueError("native command returned invalid JSON") from error


def _run_native_command(
    argv: tuple[str, ...],
    cwd: Path,
) -> NativeCommandResult:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return NativeCommandResult(
        return_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
