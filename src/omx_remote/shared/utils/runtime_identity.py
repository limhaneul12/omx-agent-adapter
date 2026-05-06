from datetime import UTC, datetime
from uuid import uuid4


def utcnow_text() -> str:
    """Builds an ISO-8601 UTC timestamp text value.

    Returns:
        str: Current UTC timestamp rendered with timezone information.
    """
    timestamp_text: str = datetime.now(UTC).isoformat()
    return timestamp_text


def build_scoped_id(target: str) -> str:
    """Builds an adapter-scoped identifier with a target prefix.

    Args:
        target [str]: Identifier target prefix such as `goal`, `team`, or another adapter-owned scope.

    Returns:
        str: Scoped identifier using the target prefix plus a short random suffix.

    Raises:
        ValueError: Raised when the target prefix is blank.
    """
    normalized_target: str = target.strip()
    if normalized_target == "":
        raise ValueError("target must not be blank")

    scoped_id: str = f"{normalized_target}-{uuid4().hex[:12]}"
    return scoped_id
