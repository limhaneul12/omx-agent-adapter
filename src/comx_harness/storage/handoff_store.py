from pathlib import Path

from comx_harness.schemas.handoff_schemas import HandoffRecord
from comx_harness.storage.json_file_store import read_json, write_model
from comx_harness.storage.workspace_layout import WorkspaceLayout


class HandoffStore:
    """Persist cross-runtime handoff provenance records."""

    def __init__(self, layout: WorkspaceLayout) -> None:
        self.layout = layout

    def write(self, handoff: HandoffRecord) -> Path:
        path = self.layout.handoff_path(handoff.handoff_id)
        written_path = write_model(path=path, model=handoff)
        return written_path

    def read(self, handoff_id: str) -> HandoffRecord:
        path = self.layout.handoff_path(handoff_id)
        payload = read_json(path)
        handoff = HandoffRecord.model_validate(payload)
        return handoff
