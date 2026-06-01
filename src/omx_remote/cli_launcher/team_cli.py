import typer

from omx_remote.cli_launcher.team_launcher.team_admin_cli import (
    register_team_admin_commands,
)
from omx_remote.cli_launcher.team_launcher.team_approval_cli import (
    register_team_approval_commands,
)
from omx_remote.cli_launcher.team_launcher.team_cleanup_cli import (
    register_team_cleanup_commands,
)
from omx_remote.cli_launcher.team_launcher.team_mailbox_cli import (
    register_team_mailbox_commands,
)
from omx_remote.cli_launcher.team_launcher.team_message_cli import (
    register_team_message_commands,
)
from omx_remote.cli_launcher.team_launcher.team_read_cli import (
    register_team_read_commands,
)
from omx_remote.cli_launcher.team_launcher.team_shutdown_cli import (
    register_team_shutdown_commands,
)
from omx_remote.cli_launcher.team_launcher.team_task_cli import (
    register_team_task_commands,
)

team_app = typer.Typer(
    help="Read OMX team runtime and team API state.", add_completion=False
)

register_team_read_commands(team_app)
register_team_message_commands(team_app)
register_team_task_commands(team_app)
register_team_approval_commands(team_app)
register_team_mailbox_commands(team_app)
register_team_shutdown_commands(team_app)
register_team_cleanup_commands(team_app)
register_team_admin_commands(team_app)
