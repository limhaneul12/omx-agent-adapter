from collections.abc import Callable
from typing import cast

from omx_remote.adapter_types.execution_types import (
    ExecCommandExecutionNormalizedPayload,
    ExecMessageNormalizedPayload,
    ExecOutputNormalizedPayload,
    ExecToolCallNormalizedPayload,
    ExecToolResultNormalizedPayload,
    ExecutionContract,
    ExecutionPayload,
    RoutedExecutionPayload,
)
from omx_remote.adapter_types.type_contract.execution_contract_type import (
    PROMOTABLE_EXECUTION_PAYLOAD_TYPES,
)
from omx_remote.schemas.execution.event_schemas import (
    ExecCommandExecution,
    ExecMessage,
    ExecOutput,
    ExecToolCall,
    ExecToolResult,
)
from omx_remote.shared.exceptions import UnsupportedExecutionPayloadError
from omx_remote.shared.omx_enums.execution_enums import PromotableExecutionPayloadType


def promote_exec_command_execution(
    payload: ExecutionPayload,
) -> ExecCommandExecution:
    """Promotes a raw command-execution payload into a stable execution contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload whose fields should become a command-execution contract.

    Returns:
        ExecCommandExecution: Stable command-execution contract built from the normalized raw payload.
    """
    normalized_payload = ExecCommandExecutionNormalizedPayload(
        kind="command_execution",
        command=payload["command"],
        aggregated_output=payload["aggregated_output"],
        exit_code=payload["exit_code"],
        status=payload["status"],
    )
    result: ExecCommandExecution = ExecCommandExecution.model_validate(
        normalized_payload
    )
    return result


def promote_exec_message(payload: ExecutionPayload) -> ExecMessage:
    """Promotes a raw message payload into a stable execution contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload whose fields should become an execution message contract.

    Returns:
        ExecMessage: Stable execution message contract built from the normalized raw payload.
    """
    normalized_payload = ExecMessageNormalizedPayload(
        kind="message",
        text=payload["text"],
    )
    result: ExecMessage = ExecMessage.model_validate(normalized_payload)
    return result


def promote_exec_output(payload: ExecutionPayload) -> ExecOutput:
    """Promotes a raw output payload into a stable execution contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload whose fields should become an execution output contract.

    Returns:
        ExecOutput: Stable execution output contract built from the normalized raw payload.
    """
    normalized_payload = ExecOutputNormalizedPayload(
        kind="output_text",
        text=payload["text"],
    )
    result: ExecOutput = ExecOutput.model_validate(normalized_payload)
    return result


def promote_exec_tool_call(payload: ExecutionPayload) -> ExecToolCall:
    """Promotes a raw tool-call payload into a stable execution contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload whose fields should become a tool-call contract.

    Returns:
        ExecToolCall: Stable execution tool-call contract built from the normalized raw payload.
    """
    normalized_payload = ExecToolCallNormalizedPayload(
        kind="tool_call",
        tool_name=payload["tool_name"],
        call_id=payload["call_id"],
        arguments=payload["arguments"],
    )
    result: ExecToolCall = ExecToolCall.model_validate(normalized_payload)
    return result


def promote_exec_tool_result(payload: ExecutionPayload) -> ExecToolResult:
    """Promotes a raw tool-result payload into a stable execution contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload whose fields should become a tool-result contract.

    Returns:
        ExecToolResult: Stable execution tool-result contract built from the normalized raw payload.
    """
    normalized_payload = ExecToolResultNormalizedPayload(
        kind="tool_result",
        tool_name=payload["tool_name"],
        call_id=payload["call_id"],
        text=payload["text"],
    )
    result: ExecToolResult = ExecToolResult.model_validate(normalized_payload)
    return result


type ExecutionContractPromoter = Callable[[ExecutionPayload], ExecutionContract]


EXECUTION_CONTRACT_PROMOTERS: dict[
    PromotableExecutionPayloadType,
    ExecutionContractPromoter,
] = {
    PromotableExecutionPayloadType.MESSAGE: promote_exec_message,
    PromotableExecutionPayloadType.OUTPUT_TEXT: promote_exec_output,
    PromotableExecutionPayloadType.COMMAND_EXECUTION: promote_exec_command_execution,
    PromotableExecutionPayloadType.TOOL_CALL: promote_exec_tool_call,
    PromotableExecutionPayloadType.TOOL_RESULT: promote_exec_tool_result,
}


def promote_execution_contract(payload: ExecutionPayload) -> ExecutionContract:
    """Promotes one raw execution payload into a stable execution contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload whose type decides the contract promotion lane.

    Returns:
        ExecutionContract: Stable execution contract built from the raw payload.

    Raises:
        UnsupportedExecutionPayloadError: Raised when the payload type is unsupported.
    """
    payload_type: object | None = payload.get("type")
    if not isinstance(payload_type, str):
        raise UnsupportedExecutionPayloadError(
            f"unsupported execution payload type: {payload_type}"
        )

    try:
        promotable_payload_type = PromotableExecutionPayloadType(payload_type)
    except ValueError as error:
        raise UnsupportedExecutionPayloadError(
            f"unsupported execution payload type: {payload_type}"
        ) from error

    promoter: ExecutionContractPromoter = EXECUTION_CONTRACT_PROMOTERS[
        promotable_payload_type
    ]
    result: ExecutionContract = promoter(payload)
    return result

def split_event_payloads(payload: ExecutionPayload) -> list[ExecutionPayload]:
    """Splits wrapped execution events into promotable payloads.

    Args:
        payload [ExecutionPayload]: Raw execution event payload inspected for an item-completed body before contract promotion.

    Returns:
        list[ExecutionPayload]: Payload list that downstream promotion can inspect one item at a time.
    """
    event_type: object | None = payload.get("type")

    if event_type == "item.completed":
        item: object | None = payload.get("item")
        if isinstance(item, dict):
            item_payload: ExecutionPayload = cast(ExecutionPayload, item)
            if is_promotable_execution_payload(item_payload):
                split_payloads: list[ExecutionPayload] = [item_payload]
                return split_payloads

    split_payloads: list[ExecutionPayload] = [payload]
    return split_payloads


def is_promotable_execution_payload(payload: ExecutionPayload) -> bool:
    """Checks whether one raw execution payload can become a stable contract.

    Args:
        payload [ExecutionPayload]: Raw execution payload inspected before contract promotion.

    Returns:
        bool: `True` when the payload type matches a supported execution contract, otherwise `False`.
    """
    payload_type: object | None = payload.get("type")
    is_promotable: bool = isinstance(payload_type, str) and (
        payload_type in PROMOTABLE_EXECUTION_PAYLOAD_TYPES
    )
    return is_promotable


def route_execution_payload(payload: ExecutionPayload) -> RoutedExecutionPayload:
    """Routes one raw execution payload to promotion or raw passthrough.

    Args:
        payload [ExecutionPayload]: Raw execution payload after transport parsing and event splitting.

    Returns:
        RoutedExecutionPayload: Promoted execution contract for supported payload types, otherwise the raw payload passthrough lane.
    """
    if not is_promotable_execution_payload(payload):
        passthrough_payload: ExecutionPayload = payload
        return passthrough_payload

    contract: ExecutionContract = promote_execution_contract(payload)
    return contract

