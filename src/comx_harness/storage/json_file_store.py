from pathlib import Path

import orjson
from pydantic import BaseModel


def write_model(path: Path, model: BaseModel) -> Path:
    payload = model.model_dump(mode="json")
    write_json(path=path, payload=payload)
    return path


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_bytes(
        orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
    )
    temporary_path.replace(path)


def read_json(path: Path) -> object:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = orjson.loads(path.read_bytes())
    return payload
