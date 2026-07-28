from dataclasses import dataclass
from pathlib import Path

from comx_harness.storage.event_store import EventStore
from comx_harness.storage.handoff_store import HandoffStore
from comx_harness.storage.idempotency_store import IdempotencyStore
from comx_harness.storage.run_store import RunStore
from comx_harness.storage.workspace_layout import WorkspaceLayout


@dataclass(frozen=True, slots=True)
class HarnessStorage:
    layout: WorkspaceLayout
    runs: RunStore
    events: EventStore
    handoffs: HandoffStore
    idempotency: IdempotencyStore


def open_storage(workspace: str | Path) -> HarnessStorage:
    layout = WorkspaceLayout.from_workspace(workspace)
    storage = HarnessStorage(
        layout=layout,
        runs=RunStore(layout),
        events=EventStore(layout),
        handoffs=HandoffStore(layout),
        idempotency=IdempotencyStore(layout),
    )
    return storage
