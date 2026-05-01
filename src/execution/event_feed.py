import orjson

from execution.payload_mapping import split_event_payloads


def decode_event_lines(payload: str) -> list[dict]:
    events: list[dict] = []
    for line in payload.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        events.extend(split_event_payloads(orjson.loads(line)))
    return events
