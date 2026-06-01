from pathlib import Path

import orjson
from pydantic import BaseModel

from omx_remote.runtime.commands.rendering.command_output_redaction import (
    redact_json_artifact,
)
from omx_remote.shared.utils.json_model_dump import (
    json_value_from_object,
    model_json_value,
)


def write_redacted_json_artifact(path: Path, value: object) -> None:
    """Write one redacted command-run JSON artifact.

    Args:
        path: See function signature.
        value: See function signature.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    json_value = (
        model_json_value(value)
        if isinstance(value, BaseModel)
        else json_value_from_object(value, context=f"JSON artifact {path}")
    )
    redacted_value = redact_json_artifact(json_value)
    serialized_value: bytes = orjson.dumps(redacted_value, option=orjson.OPT_INDENT_2)
    path.write_bytes(serialized_value)
