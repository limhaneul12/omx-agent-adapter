from collections.abc import Callable
from threading import Event
from time import monotonic, sleep

from comx_harness.ade.background_refresh import BackgroundRefreshCoordinator


def test_refresh_request_returns_while_slow_reader_runs_off_ui_thread() -> None:
    scheduled: list[Callable[[], None]] = []
    reader_started = Event()
    reader_release = Event()
    results: list[str] = []
    errors: list[Exception] = []

    def schedule(delay_ms: int, callback: Callable[[], None]) -> object:
        assert delay_ms >= 0
        scheduled.append(callback)
        return object()

    def slow_reader() -> str:
        reader_started.set()
        reader_release.wait(timeout=2)
        return "fresh"

    coordinator = BackgroundRefreshCoordinator[str](
        schedule=schedule,
        poll_interval_ms=1,
    )
    started = monotonic()
    coordinator.request(
        load=slow_reader,
        on_result=results.append,
        on_error=errors.append,
    )
    request_seconds = monotonic() - started
    try:
        assert reader_started.wait(timeout=1)
        assert request_seconds < 0.2
        assert results == []

        reader_release.set()
        deadline = monotonic() + 2
        while not results and monotonic() < deadline:
            callbacks = tuple(scheduled)
            scheduled.clear()
            for callback in callbacks:
                callback()
            sleep(0.01)

        assert results == ["fresh"]
        assert errors == []
    finally:
        reader_release.set()
        coordinator.close()


def test_refresh_keeps_only_the_latest_pending_request() -> None:
    scheduled: list[Callable[[], None]] = []
    first_reader_started = Event()
    first_reader_release = Event()
    reads: list[str] = []
    results: list[str] = []
    errors: list[Exception] = []

    def schedule(delay_ms: int, callback: Callable[[], None]) -> object:
        assert delay_ms >= 0
        scheduled.append(callback)
        return object()

    def first_reader() -> str:
        reads.append("first")
        first_reader_started.set()
        first_reader_release.wait(timeout=2)
        return "first"

    def second_reader() -> str:
        reads.append("second")
        return "second"

    def latest_reader() -> str:
        reads.append("latest")
        return "latest"

    coordinator = BackgroundRefreshCoordinator[str](
        schedule=schedule,
        poll_interval_ms=1,
    )
    coordinator.request(
        load=first_reader,
        on_result=results.append,
        on_error=errors.append,
    )
    try:
        assert first_reader_started.wait(timeout=1)
        coordinator.request(
            load=second_reader,
            on_result=results.append,
            on_error=errors.append,
        )
        coordinator.request(
            load=latest_reader,
            on_result=results.append,
            on_error=errors.append,
        )
        first_reader_release.set()

        deadline = monotonic() + 2
        while len(results) < 2 and monotonic() < deadline:
            callbacks = tuple(scheduled)
            scheduled.clear()
            for callback in callbacks:
                callback()
            sleep(0.01)

        assert reads == ["first", "latest"]
        assert results == ["first", "latest"]
        assert errors == []
    finally:
        first_reader_release.set()
        coordinator.close()


def test_refresh_close_suppresses_completed_result_callback() -> None:
    scheduled: list[Callable[[], None]] = []
    reader_started = Event()
    reader_release = Event()
    results: list[str] = []
    errors: list[Exception] = []

    def schedule(delay_ms: int, callback: Callable[[], None]) -> object:
        assert delay_ms >= 0
        scheduled.append(callback)
        return object()

    def slow_reader() -> str:
        reader_started.set()
        reader_release.wait(timeout=2)
        return "late"

    coordinator = BackgroundRefreshCoordinator[str](
        schedule=schedule,
        poll_interval_ms=1,
    )
    coordinator.request(
        load=slow_reader,
        on_result=results.append,
        on_error=errors.append,
    )
    assert reader_started.wait(timeout=1)
    reader_release.set()
    coordinator.close()

    deadline = monotonic() + 1
    while scheduled and monotonic() < deadline:
        callbacks = tuple(scheduled)
        scheduled.clear()
        for callback in callbacks:
            callback()

    assert results == []
    assert errors == []
