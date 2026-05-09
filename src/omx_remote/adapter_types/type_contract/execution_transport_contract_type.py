from omx_remote.shared.omx_enums.execution_enums import (
    ExecutionItemStableFieldKey,
    ExecutionTransportStableFieldKey,
)

EXECUTION_ITEM_STABLE_FIELD_KEYS: frozenset[str] = frozenset(
    field_key.value for field_key in ExecutionItemStableFieldKey
)
EXECUTION_TRANSPORT_STABLE_FIELD_KEYS: frozenset[str] = frozenset(
    field_key.value for field_key in ExecutionTransportStableFieldKey
)
