from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4


def utc_timestamp() -> str:
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return timestamp


def compact_timestamp() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return timestamp


def allocate_run_id() -> str:
    run_id = f"run-{compact_timestamp()}-{uuid4().hex[:8]}"
    return run_id


def idempotent_run_id(idempotency_key: str) -> str:
    """Return the stable Run identity for one idempotent operation."""
    digest = sha256(idempotency_key.encode("utf-8")).hexdigest()
    return f"run-idem-{digest[:24]}"


def allocate_handoff_id() -> str:
    handoff_id = f"handoff-{compact_timestamp()}-{uuid4().hex[:8]}"
    return handoff_id


def idempotent_handoff_id(idempotency_key: str) -> str:
    """Return the stable provenance identity for one idempotent handoff."""
    digest = sha256(idempotency_key.encode("utf-8")).hexdigest()
    return f"handoff-idem-{digest[:24]}"
