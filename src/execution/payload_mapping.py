from schemas.execution_schemas import ExecMessage


def split_event_payloads(payload: dict) -> list[dict]:
    event_type = payload.get("type")

    if event_type == "item.completed":
        item = payload.get("item")
        if isinstance(item, dict):
            return [item]

    return [payload]


def promote_exec_message(payload: dict) -> ExecMessage:
    normalized_payload = {
        "kind": payload["type"],
        "text": payload["text"],
    }
    return ExecMessage.model_validate(normalized_payload)
