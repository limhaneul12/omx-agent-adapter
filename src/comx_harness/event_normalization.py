from __future__ import annotations

import orjson

from comx_harness.native_provider.provider_event_parsing import (
    provider_event_identity,
)
from comx_harness.schemas.lifecycle_schemas import RunEvent
from comx_harness.shared.harness_enums.lifecycle_enums import EventKind
from comx_harness.storage.harness_storage import HarnessStorage
from comx_harness.storage.time_identity import utc_timestamp


def append_run_event(
    storage: HarnessStorage,
    *,
    run_id: str,
    kind: EventKind,
    message: str,
    provider_event_type: str | None = None,
    provider_payload_json: str | None = None,
) -> None:
    """Append one ordered normalized event to a run."""
    sequence = len(storage.events.read(run_id)) + 1
    event = RunEvent(
        run_id=run_id,
        sequence=sequence,
        timestamp=utc_timestamp(),
        kind=kind,
        message=message or "provider event",
        provider_event_type=provider_event_type,
        provider_payload_json=provider_payload_json,
    )
    storage.events.append(event)


def record_provider_output(
    storage: HarnessStorage,
    run_id: str,
    stdout_text: str,
    stderr_text: str,
) -> str | None:
    """Normalize native stdout/stderr and return an observed session id."""
    session_id: str | None = None
    for line in stdout_text.splitlines():
        event_type, candidate_session_id = provider_event_identity(line)
        if session_id is None and candidate_session_id is not None:
            session_id = candidate_session_id
        payload_json = _canonical_provider_payload(line, event_type)
        append_run_event(
            storage,
            run_id=run_id,
            kind=(EventKind.PROVIDER if event_type is not None else EventKind.STDOUT),
            message=event_type or line[:500] or "stdout line",
            provider_event_type=event_type,
            provider_payload_json=payload_json,
        )
    for line in stderr_text.splitlines():
        append_run_event(
            storage,
            run_id=run_id,
            kind=EventKind.STDERR,
            message=line[:500] or "stderr line",
        )
    return session_id


def _canonical_provider_payload(line: str, event_type: str | None) -> str | None:
    if event_type is None:
        return None
    try:
        payload = orjson.loads(line)
    except orjson.JSONDecodeError:
        return None
    canonical = orjson.dumps(payload, option=orjson.OPT_SORT_KEYS).decode("utf-8")
    return canonical
