import math
from pathlib import Path

import pytest
from pydantic import BaseModel

from omx_remote.shared.utils.json_file_store import JsonFileStore, json_file_stores


class ExampleJsonModel(BaseModel):
    name: str
    count: int


def test_json_file_store_registry_reuses_store_for_equivalent_paths(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state" / "payload.json"
    equivalent_path = tmp_path / "state" / "nested" / ".." / "payload.json"

    first_store = json_file_stores.for_path(state_path)
    second_store = json_file_stores.for_path(equivalent_path)

    assert first_store is second_store
    assert first_store.path == state_path.resolve()


def test_json_file_store_writes_and_reads_mapping_without_repassing_path(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state" / "payload.json"
    store = JsonFileStore(state_path)

    store.write_mapping({"name": "alpha", "count": 2})
    result = store.read_object()

    assert result == {"name": "alpha", "count": 2}


def test_json_file_store_rejects_non_finite_float_before_mkdir(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state" / "payload.json"
    store = JsonFileStore(state_path)

    with pytest.raises(ValueError, match="JSON-compatible"):
        store.write_mapping({"value": math.nan})

    assert not state_path.parent.exists()


def test_json_file_store_write_model_creates_parent_directories(tmp_path: Path) -> None:
    state_path = tmp_path / "missing" / "nested" / "payload.json"
    store = json_file_stores.for_path(state_path)

    store.write_model(ExampleJsonModel(name="beta", count=3))

    assert state_path.exists()
    assert store.read_object() == {"name": "beta", "count": 3}
