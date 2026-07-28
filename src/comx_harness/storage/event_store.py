import orjson
from comx_harness.schemas.lifecycle_schemas import RunEvent
from comx_harness.storage.workspace_layout import WorkspaceLayout


class EventStore:
    """Append and read ordered normalized run events."""

    def __init__(self, layout: WorkspaceLayout) -> None:
        self.layout = layout

    def append(self, event: RunEvent) -> None:
        path = self.layout.run_paths(event.run_id).events
        path.parent.mkdir(parents=True, exist_ok=True)
        line = orjson.dumps(event.model_dump(mode="json")) + b"\n"
        with path.open("ab") as stream:
            stream.write(line)

    def read(self, run_id: str) -> tuple[RunEvent, ...]:
        path = self.layout.run_paths(run_id).events
        if not path.exists():
            return ()
        events: list[RunEvent] = []
        for raw_line in path.read_bytes().splitlines():
            if not raw_line.strip():
                continue
            event = RunEvent.model_validate(orjson.loads(raw_line))
            events.append(event)
        normalized_events = tuple(events)
        return normalized_events
