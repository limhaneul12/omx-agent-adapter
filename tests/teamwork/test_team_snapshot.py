import asyncio
import inspect

from schemas.teamwork_schemas import TeamStatusRequest
from teamwork import team_snapshot


def test_read_team_status_is_async() -> None:
    assert inspect.iscoroutinefunction(team_snapshot.read_team_status)


def test_read_team_status_accepts_typed_request() -> None:
    coroutine = team_snapshot.read_team_status(TeamStatusRequest(team_name="alpha"))

    assert inspect.isawaitable(coroutine)
    asyncio.run(coroutine)
