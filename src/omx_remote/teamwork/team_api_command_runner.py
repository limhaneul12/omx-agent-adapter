from collections.abc import Callable

import msgspec
import orjson

from omx_remote.adapter_types.teams_type.team_api_control_payloads import (
    TeamApiControlPayload,
    TeamApiOptionalBool,
    TeamApiOptionalInt,
    TeamApiOptionalString,
    TeamApiOptionalStringItems,
    TeamApiStringItems,
)
from omx_remote.execution.async_boundary import run_blocking_call
from omx_remote.schemas.invoke_command_schemas import OmxCommandResult


def _optional_string(value: str | None) -> TeamApiOptionalString:
    """Convert an optional request string to an omitted msgspec field value.

    Args:
        value [str | None]: Optional request value.

    Returns:
        TeamApiOptionalString: Original string or `msgspec.UNSET` when omitted.
    """
    result: TeamApiOptionalString = msgspec.UNSET if value is None else value
    return result


def _optional_bool(value: bool | None) -> TeamApiOptionalBool:
    """Convert an optional request bool to an omitted msgspec field value.

    Args:
        value [bool | None]: Optional request value.

    Returns:
        TeamApiOptionalBool: Original bool or `msgspec.UNSET` when omitted.
    """
    result: TeamApiOptionalBool = msgspec.UNSET if value is None else value
    return result


def _optional_int(value: int | None) -> TeamApiOptionalInt:
    """Convert an optional request int to an omitted msgspec field value.

    Args:
        value [int | None]: Optional request value.

    Returns:
        TeamApiOptionalInt: Original int or `msgspec.UNSET` when omitted.
    """
    result: TeamApiOptionalInt = msgspec.UNSET if value is None else value
    return result


def _optional_string_items(
    values: TeamApiStringItems | None,
) -> TeamApiOptionalStringItems:
    """Convert optional string items to an omitted msgspec field value.

    Args:
        values [TeamApiStringItems | None]: Optional request tuple.

    Returns:
        TeamApiOptionalStringItems: Original tuple or `msgspec.UNSET` when omitted.
    """
    result: TeamApiOptionalStringItems = msgspec.UNSET if values is None else values
    return result


def _nonempty_string_items(values: TeamApiStringItems) -> TeamApiOptionalStringItems:
    """Convert an empty tuple into an omitted msgspec field value.

    Args:
        values [TeamApiStringItems]: Required request tuple where emptiness means omission.

    Returns:
        TeamApiOptionalStringItems: Non-empty tuple or `msgspec.UNSET` when empty.
    """
    result: TeamApiOptionalStringItems = values if values else msgspec.UNSET
    return result


async def _run_team_api_command(
    action: str,
    payload: TeamApiControlPayload,
    command_runner: Callable[..., OmxCommandResult],
) -> OmxCommandResult:
    """Run one Team API OMX command.

    Args:
        action [str]: Team API action name.
        payload [TeamApiControlPayload]: Typed JSON payload for the action.
        command_runner [Callable[..., OmxCommandResult]]: Command execution seam.

    Returns:
        OmxCommandResult: Completed OMX command result.
    """
    payload_json = orjson.dumps(msgspec.to_builtins(payload)).decode()
    command_arguments: tuple[str, ...] = (
        "team",
        "api",
        action,
        "--input",
        payload_json,
        "--json",
    )
    result: OmxCommandResult = await run_blocking_call(
        command_runner,
        arguments=command_arguments,
    )
    return result


