from __future__ import annotations

import json
from urllib.request import urlopen


def test_probe_alexandria_openapi() -> None:
    with urlopen("http://127.0.0.1:8000/openapi.json", timeout=10) as response:
        spec = json.load(response)

    selected: dict[str, object] = {}
    for path, methods in spec.get("paths", {}).items():
        lowered = path.lower()
        if any(token in lowered for token in ("obsidian", "note", "vault", "reindex", "search")):
            selected[path] = methods

    assert False, json.dumps(selected, ensure_ascii=False, indent=2)
