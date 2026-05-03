import orjson

from transport_types import TransportObject


def load_json_object_stdout[SurfaceErrorT: Exception](
    stdout: str,
    *,
    command_name: str,
    error_type: type[SurfaceErrorT],
) -> TransportObject:
    """Parses command stdout as a JSON object for adapter transport seams."""
    if not stdout:
        raise error_type(f"{command_name} returned no stdout output")

    try:
        parsed_payload: object = orjson.loads(stdout)
    except orjson.JSONDecodeError as error:
        raise error_type(
            f"{command_name} returned unparseable JSON output"
        ) from error

    if not isinstance(parsed_payload, dict):
        raise error_type(f"{command_name} returned a non-object JSON payload")

    result: TransportObject = dict(parsed_payload)
    return result
