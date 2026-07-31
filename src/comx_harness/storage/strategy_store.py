from __future__ import annotations

import orjson
from comx_harness.schemas.strategy_schemas import (
    StrategyEvent,
    StrategyRecord,
)
from comx_harness.storage.json_file_store import read_json, write_model
from comx_harness.storage.workspace_layout import WorkspaceLayout


class StrategyStore:
    """Persist one workspace-local Strategy aggregate and its ordered events."""

    def __init__(self, layout: WorkspaceLayout) -> None:
        self.layout = layout

    def write(self, record: StrategyRecord) -> StrategyRecord:
        path = self.layout.strategy_paths(record.definition.strategy_id).record
        write_model(path, record)
        return record

    def read(self, strategy_id: str) -> StrategyRecord:
        path = self.layout.strategy_paths(strategy_id).record
        return StrategyRecord.model_validate(read_json(path))

    def append_event(self, event: StrategyEvent) -> StrategyEvent:
        path = self.layout.strategy_paths(event.strategy_id).events
        path.parent.mkdir(parents=True, exist_ok=True)
        line = orjson.dumps(event.model_dump(mode="json")) + b"\n"
        with path.open("ab") as stream:
            stream.write(line)
        return event

    def read_events(self, strategy_id: str) -> tuple[StrategyEvent, ...]:
        path = self.layout.strategy_paths(strategy_id).events
        if not path.exists():
            return ()
        events: list[StrategyEvent] = []
        for raw_line in path.read_bytes().splitlines():
            if not raw_line.strip():
                continue
            events.append(StrategyEvent.model_validate(orjson.loads(raw_line)))
        return tuple(events)

    def list_records(self) -> tuple[StrategyRecord, ...]:
        if not self.layout.strategies_root.exists():
            return ()
        records: list[StrategyRecord] = []
        for record_path in self.layout.strategies_root.glob("*/strategy.json"):
            try:
                records.append(StrategyRecord.model_validate(read_json(record_path)))
            except (OSError, ValueError):
                continue
        records.sort(key=lambda record: record.updated_at, reverse=True)
        return tuple(records)
