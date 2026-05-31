from typing import Final

SESSION_IDENTIFIER_EXTRA_CHARACTERS: Final[frozenset[str]] = frozenset({"-", "_"})


def validate_session_identifier(session_id: str) -> str:
    """Validate a durable session identifier as one safe path component.

    Args:
        session_id [str]: Candidate session identifier.

    Returns:
        str: Validated session identifier.

    Raises:
        ValueError: Raised when the identifier is empty or path-unsafe.
    """
    if not session_id or not session_id[0].isalnum():
        raise ValueError(
            "session id must start with a letter or digit and use only "
            "letters, digits, '-' or '_'"
        )
    if not all(
        character.isalnum() or character in SESSION_IDENTIFIER_EXTRA_CHARACTERS
        for character in session_id
    ):
        raise ValueError(
            "session id must start with a letter or digit and use only "
            "letters, digits, '-' or '_'"
        )
    validated_session_id = session_id
    return validated_session_id
