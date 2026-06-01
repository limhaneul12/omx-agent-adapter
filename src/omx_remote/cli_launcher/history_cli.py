import asyncio

import typer

from omx_remote.history.session_search import search_sessions
from omx_remote.schemas.history_session_schemas import SessionSearchRequest

history_app = typer.Typer(
    help="Read OMX session history search results.", add_completion=False
)


@history_app.command("session-search")
def history_session_search(
    query: str = typer.Option(
        ..., "--query", help="Search query to run against OMX session history."
    ),
    limit: int = typer.Option(
        10, "--limit", help="Maximum number of results to return."
    ),
) -> None:
    """Read normalized OMX session-search results.

    Args:
        query [str]: Function argument.
        limit [int]: Function argument.
    """
    result = asyncio.run(
        search_sessions(SessionSearchRequest(query=query, limit=limit))
    )
    typer.echo(result.model_dump_json(indent=2))
