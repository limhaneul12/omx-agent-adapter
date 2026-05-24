"""Async boundary helpers for blocking call sites."""

from __future__ import annotations

from collections.abc import Callable

from asyncer import asyncify


async def run_blocking_call[**P, R](
    function: Callable[P, R],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    """Run a blocking callable from an async boundary.

    Args:
        function [Callable[P, R]]: Blocking callable to run in a worker thread.
        *args [P.args]: Positional arguments forwarded to the callable.
        **kwargs [P.kwargs]: Keyword arguments forwarded to the callable.

    Returns:
        R: The callable return value.
    """
    result: R = await asyncify(function)(*args, **kwargs)
    return result
