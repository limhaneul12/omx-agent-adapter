import orjson


def quote_omx_task(task: str) -> str:
    """Quotes one OMX task string for display inside launch hints.

    Args:
        task [str]: Raw task text that should be represented as JSON string text.

    Returns:
        str: JSON-quoted task text suitable for shell-facing hints.
    """
    quoted_task: str = orjson.dumps(task).decode()
    return quoted_task
