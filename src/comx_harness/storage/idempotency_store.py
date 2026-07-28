import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from hashlib import sha256
from time import monotonic, sleep

import orjson
from comx_harness.schemas.common_schemas import StrictModel
from comx_harness.schemas.execution_schemas import (
    IdempotencyBinding,
)
from comx_harness.shared.exceptions.idempotency_exceptions import (
    IdempotencyLockTimeoutError,
)
from comx_harness.storage.json_file_store import read_json, write_model
from comx_harness.storage.workspace_layout import WorkspaceLayout

_IDEMPOTENCY_LOCK_TIMEOUT_SECONDS = 10.0
_IDEMPOTENCY_LOCK_POLL_SECONDS = 0.01


def idempotency_request_sha256(request: StrictModel) -> str:
    """Hash the operation fields while excluding its retry token."""
    payload = request.model_dump(mode="json", exclude={"idempotency_key"})
    encoded = orjson.dumps(payload, option=orjson.OPT_SORT_KEYS)
    digest = sha256(encoded).hexdigest()
    return digest


class IdempotencyStore:
    """Coordinate run-producing operations by caller-supplied retry token."""

    def __init__(self, layout: WorkspaceLayout) -> None:
        self.layout = layout

    def resolve(self, key: str) -> IdempotencyBinding | None:
        path = self.layout.idempotency_path(key)
        if not path.exists():
            return None
        payload = read_json(path)
        binding = IdempotencyBinding.model_validate(payload)
        return binding

    def bind(self, key: str, request: StrictModel, run_id: str) -> None:
        path = self.layout.idempotency_path(key)
        binding = IdempotencyBinding(
            key_sha256=sha256(key.encode()).hexdigest(),
            request_sha256=idempotency_request_sha256(request),
            run_id=run_id,
        )
        write_model(path=path, model=binding)

    @contextmanager
    def claim(
        self,
        key: str,
        *,
        timeout_seconds: float = _IDEMPOTENCY_LOCK_TIMEOUT_SECONDS,
    ) -> Iterator[None]:
        """Serialize one key while its operation result is registered."""
        lock_path = self.layout.idempotency_lock_path(key)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        deadline = monotonic() + timeout_seconds
        with lock_path.open("a+b") as lock_stream:
            while True:
                try:
                    fcntl.flock(
                        lock_stream.fileno(),
                        fcntl.LOCK_EX | fcntl.LOCK_NB,
                    )
                    break
                except BlockingIOError as error:
                    if monotonic() >= deadline:
                        raise IdempotencyLockTimeoutError(
                            "timed out while coordinating an idempotent operation"
                        ) from error
                    sleep(_IDEMPOTENCY_LOCK_POLL_SECONDS)
            try:
                yield
            finally:
                fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
