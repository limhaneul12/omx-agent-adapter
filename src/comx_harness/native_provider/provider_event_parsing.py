import orjson


def provider_event_identity(line: str) -> tuple[str | None, str | None]:
    """Extract provider event type and session identity at the JSONL seam."""
    try:
        payload = orjson.loads(line)
    except orjson.JSONDecodeError:
        return None, None
    if not isinstance(payload, dict):
        return None, None
    event_type_value = payload.get("type")
    event_type = event_type_value if isinstance(event_type_value, str) else None
    session_id: str | None = None
    for key in ("thread_id", "session_id", "conversation_id"):
        candidate = payload.get(key)
        if isinstance(candidate, str) and candidate:
            session_id = candidate
            break
    if session_id is None:
        thread = payload.get("thread")
        if isinstance(thread, dict):
            candidate = thread.get("id")
            if isinstance(candidate, str) and candidate:
                session_id = candidate
    identity = (event_type, session_id)
    return identity
