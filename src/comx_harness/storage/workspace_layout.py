from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RunPaths:
    directory: Path
    plan: Path
    record: Path
    result: Path
    stdout: Path
    stderr: Path
    events: Path


@dataclass(frozen=True, slots=True)
class StrategyPaths:
    directory: Path
    record: Path
    events: Path
    request: Path
    launch: Path
    result: Path
    stdout: Path
    stderr: Path


@dataclass(frozen=True, slots=True)
class MissionPaths:
    directory: Path
    record: Path
    git_before: Path
    git_evidence: Path


@dataclass(frozen=True, slots=True)
class WorkspaceLayout:
    workspace: Path
    root: Path
    runs_root: Path
    handoffs_root: Path
    idempotency_root: Path
    strategies_root: Path
    missions_root: Path

    @classmethod
    def from_workspace(cls, workspace: str | Path) -> "WorkspaceLayout":
        resolved_workspace = Path(workspace).resolve()
        root = resolved_workspace / ".comx-agent" / "v2"
        layout = cls(
            workspace=resolved_workspace,
            root=root,
            runs_root=root / "runs",
            handoffs_root=root / "handoffs",
            idempotency_root=root / "idempotency",
            strategies_root=root / "strategies",
            missions_root=root / "missions",
        )
        return layout

    def run_paths(self, run_id: str) -> RunPaths:
        directory = self.runs_root / run_id
        paths = RunPaths(
            directory=directory,
            plan=directory / "plan.json",
            record=directory / "run.json",
            result=directory / "result.md",
            stdout=directory / "stdout.log",
            stderr=directory / "stderr.log",
            events=directory / "events.jsonl",
        )
        return paths

    def strategy_paths(self, strategy_id: str) -> StrategyPaths:
        directory = self.strategies_root / strategy_id
        return StrategyPaths(
            directory=directory,
            record=directory / "strategy.json",
            events=directory / "events.jsonl",
            request=directory / "request.json",
            launch=directory / "launch.json",
            result=directory / "result.json",
            stdout=directory / "worker.stdout.log",
            stderr=directory / "worker.stderr.log",
        )

    def _mission_paths(self, mission_id: str) -> MissionPaths:
        directory = self.missions_root / mission_id
        return MissionPaths(
            directory=directory,
            record=directory / "mission.json",
            git_before=directory / "git-before.json",
            git_evidence=directory / "git-policy-evidence.json",
        )

    def handoff_path(self, handoff_id: str) -> Path:
        path = self.handoffs_root / f"{handoff_id}.json"
        return path

    def idempotency_path(self, key: str) -> Path:
        digest = sha256(key.encode()).hexdigest()
        path = self.idempotency_root / f"{digest}.json"
        return path

    def idempotency_lock_path(self, key: str) -> Path:
        digest = sha256(key.encode()).hexdigest()
        path = self.idempotency_root / "locks" / f"{digest}.lock"
        return path
