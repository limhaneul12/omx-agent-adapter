from schemas.teamwork_schemas import TeamStatusRequest


async def read_team_status(request: TeamStatusRequest) -> None:
    """Reads team status through the typed teamwork surface."""

    _ = request
