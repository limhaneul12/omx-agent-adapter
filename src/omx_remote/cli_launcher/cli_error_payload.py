import orjson

from omx_remote.adapter_types.json_types import JsonObject


def format_failed_cli_error_payload(error: Exception) -> str:
    """Format a failed CLI command error payload.

    Args:
        error [Exception]: Error raised while handling a CLI command.

    Returns:
        str: JSON error payload using the shared `ok: false` shape.
    """
    error_payload = _format_cli_error_payload(
        error,
        status_key="ok",
        status_value=False,
    )
    return error_payload


def format_invalid_cli_error_payload(
    error: Exception,
    config_path: str | None = None,
) -> str:
    """Format an invalid CLI request or config error payload.

    Args:
        error [Exception]: Error raised while validating request or config.
        config_path [str | None]: Optional config path to include.

    Returns:
        str: JSON error payload using the shared `valid: false` shape.
    """
    extra_fields: JsonObject | None = None
    if config_path is not None:
        extra_fields = {"config_path": config_path}

    error_payload = _format_cli_error_payload(
        error,
        status_key="valid",
        status_value=False,
        extra_fields=extra_fields,
    )
    return error_payload


def _format_cli_error_payload(
    error: Exception,
    status_key: str,
    status_value: bool,
    extra_fields: JsonObject | None = None,
) -> str:
    """Format the shared JSON CLI error transport shape.

    Args:
        error [Exception]: Error raised while handling a CLI command.
        status_key [str]: Boolean status key to include in the payload.
        status_value [bool]: Boolean status value to include in the payload.
        extra_fields [JsonObject | None]: Optional additional JSON fields.

    Returns:
        str: Indented JSON error payload.
    """
    payload: JsonObject = {status_key: status_value, "error": str(error)}
    if extra_fields is not None:
        payload.update(extra_fields)
    error_payload: str = orjson.dumps(payload, option=orjson.OPT_INDENT_2).decode()
    return error_payload
