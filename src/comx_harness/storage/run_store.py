from pathlib import Path

from comx_harness.schemas.execution_schemas import ExecutionPlan
from comx_harness.schemas.lifecycle_schemas import RunRecord
from comx_harness.storage.json_file_store import read_json, write_model
from comx_harness.storage.workspace_layout import WorkspaceLayout


class RunStore:
    """Persist run plans and normalized run records."""

    def __init__(self, layout: WorkspaceLayout) -> None:
        self.layout = layout

    def ensure_run(self, run_id: str) -> Path:
        directory = self.layout.run_paths(run_id).directory
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def write_plan(self, plan: ExecutionPlan) -> Path:
        path = self.layout.run_paths(plan.run_id).plan
        written_path = write_model(path=path, model=plan)
        return written_path

    def read_plan(self, run_id: str) -> ExecutionPlan:
        payload = read_json(self.layout.run_paths(run_id).plan)
        plan = ExecutionPlan.model_validate(payload)
        return plan

    def write_record(self, record: RunRecord) -> Path:
        path = self.layout.run_paths(record.run_id).record
        written_path = write_model(path=path, model=record)
        return written_path

    def read_record(self, run_id: str) -> RunRecord:
        payload = read_json(self.layout.run_paths(run_id).record)
        record = RunRecord.model_validate(payload)
        return record
