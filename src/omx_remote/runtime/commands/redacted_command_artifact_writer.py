from pathlib import Path
from typing import cast

import orjson

from omx_remote.adapter_types.json_types import JsonValue
from omx_remote.runtime.commands.command_output_redaction import redact_json_artifact


def write_redacted_json_artifact(path: Path, value: object) -> None:
    """Write one redacted command-run JSON artifact.

    Args:
        path: See function signature.
        value: See function signature.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    redacted_value: JsonValue = redact_json_artifact(cast(JsonValue, value))
    serialized_value: bytes = orjson.dumps(redacted_value, option=orjson.OPT_INDENT_2)
    path.write_bytes(serialized_value)
