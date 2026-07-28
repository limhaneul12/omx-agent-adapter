from __future__ import annotations

import os
import tempfile
from pathlib import Path

import orjson
from comx_harness.schemas.ade_schemas import (
    AdeCatalog,
    AdeStateSettings,
    AdeViewContext,
)
from pydantic import BaseModel


class AdeStateStore:
    """Atomic persistence for ADE navigation state."""

    def __init__(self, settings: AdeStateSettings | None = None) -> None:
        self._settings = settings or AdeStateSettings.from_environment()

    @property
    def state_root(self) -> Path:
        return self._settings.state_root

    def load_catalog(self) -> AdeCatalog:
        if not self._catalog_path.exists():
            return AdeCatalog(projects=(), workspaces=())
        return AdeCatalog.model_validate_json(self._catalog_path.read_bytes())

    def save_catalog(self, catalog: AdeCatalog) -> None:
        self._write_model(path=self._catalog_path, model=catalog)

    def load_view_context(self) -> AdeViewContext:
        if not self._view_context_path.exists():
            return AdeViewContext()
        return AdeViewContext.model_validate_json(self._view_context_path.read_bytes())

    def save_view_context(self, context: AdeViewContext) -> None:
        self._write_model(path=self._view_context_path, model=context)

    @property
    def _catalog_path(self) -> Path:
        return self.state_root / "catalog.json"

    @property
    def _view_context_path(self) -> Path:
        return self.state_root / "view-context.json"

    @staticmethod
    def _write_model(*, path: Path, model: BaseModel) -> None:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # The catalog reveals local repository paths and remains single-user state.
        path.parent.chmod(0o700)
        payload = orjson.dumps(
            model.model_dump(mode="json"),
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        )
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as temporary_file:
                temporary_file.write(payload)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            temporary_path.replace(path)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise
