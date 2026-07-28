from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass

Schedule = Callable[[int, Callable[[], None]], object]


@dataclass(frozen=True, slots=True)
class _RefreshRequest[RefreshValue]:
    load: Callable[[], RefreshValue]
    on_result: Callable[[RefreshValue], None]
    on_error: Callable[[Exception], None]


class BackgroundRefreshCoordinator[RefreshValue]:
    """Run slow projection reads away from the Tk event-loop thread."""

    def __init__(
        self,
        schedule: Schedule,
        poll_interval_ms: int = 50,
    ) -> None:
        if poll_interval_ms < 1:
            raise ValueError("poll_interval_ms must be positive")
        self._schedule = schedule
        self._poll_interval_ms = poll_interval_ms
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="comx-ade-refresh",
        )
        self._future: Future[RefreshValue] | None = None
        self._active_request: _RefreshRequest[RefreshValue] | None = None
        self._pending_request: _RefreshRequest[RefreshValue] | None = None
        self._closed = False

    def request(
        self,
        load: Callable[[], RefreshValue],
        on_result: Callable[[RefreshValue], None],
        on_error: Callable[[Exception], None],
    ) -> None:
        """Start a refresh or retain only the newest request while one is active."""
        if self._closed:
            return
        request = _RefreshRequest(
            load=load,
            on_result=on_result,
            on_error=on_error,
        )
        if self._future is not None:
            self._pending_request = request
            return
        self._start(request)

    def close(self) -> None:
        """Stop accepting work and finish executor teardown before Tk exits."""
        if self._closed:
            return
        self._closed = True
        self._pending_request = None
        future = self._future
        if future is not None:
            future.cancel()
        self._executor.shutdown(wait=True, cancel_futures=True)

    def _start(self, request: _RefreshRequest[RefreshValue]) -> None:
        self._active_request = request
        self._future = self._executor.submit(request.load)
        self._schedule(self._poll_interval_ms, self._poll)

    def _poll(self) -> None:
        if self._closed:
            return
        future = self._future
        request = self._active_request
        if future is None or request is None:
            return
        if not future.done():
            self._schedule(self._poll_interval_ms, self._poll)
            return
        self._future = None
        self._active_request = None
        pending = self._pending_request
        self._pending_request = None
        try:
            result = future.result()
        except Exception as error:
            request.on_error(error)
        else:
            request.on_result(result)
        if pending is not None and self._future is None and not self._closed:
            self._start(pending)
