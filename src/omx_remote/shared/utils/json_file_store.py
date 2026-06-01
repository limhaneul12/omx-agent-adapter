from collections.abc import Mapping
from pathlib import Path

import orjson
from pydantic import BaseModel

from omx_remote.adapter_types.json_types import JsonObject, JsonValue
from omx_remote.shared.json_transport import is_json_value, json_object_or_none
from omx_remote.shared.utils.json_model_dump import model_json_object


class JsonFileStore:
    """Reads and writes one JSON file path using orjson."""

    def __init__(self, path: Path) -> None:
        """Create one path-bound JSON file store.

        Args:
            path [Path]: JSON file path owned by this store.
        """
        self.path = path.resolve()

    def read_object(self) -> JsonObject | None:
        """Read a JSON object from the owned path with orjson.

        Returns:
            JsonObject | None: Parsed JSON object when the file exists and contains an object; otherwise ``None``.
        """
        try:
            raw_payload: bytes = self.path.read_bytes()
        except OSError:
            return None

        parsed_payload: object
        try:
            parsed_payload = orjson.loads(raw_payload)
        except orjson.JSONDecodeError:
            return None

        object_payload: JsonObject | None = json_object_or_none(parsed_payload)
        return object_payload

    def write_mapping(
        self,
        payload: Mapping[str, JsonValue],
        trailing_newline: bool = False,
    ) -> None:
        """Write a mapping as indented JSON to the owned path.

        Args:
            payload [Mapping[str, JsonValue]]: Mapping to serialize.
            trailing_newline [bool]: Whether to append one trailing newline byte.
        """
        if not all(
            isinstance(key, str) and is_json_value(value)
            for key, value in payload.items()
        ):
            raise ValueError("mapping payload must contain JSON-compatible values")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serialized_payload: bytes = orjson.dumps(payload, option=orjson.OPT_INDENT_2)
        if trailing_newline:
            serialized_payload += b"\n"
        self.path.write_bytes(serialized_payload)

    def write_model(self, model: BaseModel, trailing_newline: bool = False) -> None:
        """Write a Pydantic model as JSON with enum-safe transport values.

        Args:
            model [BaseModel]: Pydantic model to serialize with ``mode=\"json\"``.
            trailing_newline [bool]: Whether to append one trailing newline byte.
        """
        payload = model_json_object(model)
        self.write_mapping(payload, trailing_newline=trailing_newline)


class JsonFileStoreRegistry:
    """Provides JSON file stores by normalized path."""

    def __init__(self) -> None:
        """Create an empty path-bound JSON store registry."""
        self._stores_by_path: dict[Path, JsonFileStore] = {}

    def for_path(self, path: Path) -> JsonFileStore:
        """Return the singleton JSON store for one normalized path.

        Args:
            path [Path]: JSON file path to own.

        Returns:
            JsonFileStore: Path-bound JSON file store for the normalized path.
        """
        normalized_path: Path = path.resolve()
        existing_store: JsonFileStore | None = self._stores_by_path.get(normalized_path)
        if existing_store is not None:
            return existing_store

        store = JsonFileStore(normalized_path)
        self._stores_by_path[normalized_path] = store
        return store


json_file_stores = JsonFileStoreRegistry()


def read_required_json_object(path: Path) -> JsonObject:
    """Read a JSON object from disk or raise a boundary error.

    Args:
        path [Path]: JSON file path to read.

    Returns:
        JsonObject: Parsed JSON object.
    """
    payload: JsonObject | None = json_file_stores.for_path(path).read_object()
    if payload is None:
        raise ValueError(f"Expected JSON object in {path}")
    return payload
