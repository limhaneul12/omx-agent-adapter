from collections.abc import Mapping
from pathlib import Path

import orjson
from pydantic import BaseModel


class JsonFileStore:
    """Reads and writes one JSON file path using orjson."""

    def __init__(self, path: Path) -> None:
        """Create one path-bound JSON file store.

        Args:
            path [Path]: JSON file path owned by this store.
        """
        self.path = path.resolve()

    def read_object(self) -> dict[str, object] | None:
        """Read a JSON object from the owned path with orjson.

        Returns:
            dict[str, object] | None: Parsed JSON object when the file exists and contains an object; otherwise ``None``.
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

        if isinstance(parsed_payload, dict):
            object_payload: dict[str, object] = dict(parsed_payload)
            return object_payload

        return None

    def write_mapping(self, payload: Mapping[str, object]) -> None:
        """Write a mapping as indented JSON to the owned path.

        Args:
            payload [Mapping[str, object]]: Mapping to serialize.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        serialized_payload: bytes = orjson.dumps(payload, option=orjson.OPT_INDENT_2)
        self.path.write_bytes(serialized_payload)

    def write_model(self, model: BaseModel) -> None:
        """Write a Pydantic model as JSON with enum-safe transport values.

        Args:
            model [BaseModel]: Pydantic model to serialize with ``mode=\"json\"``.
        """
        payload: dict[str, object] = model.model_dump(mode="json")
        self.write_mapping(payload)


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
