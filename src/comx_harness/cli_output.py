from __future__ import annotations

from typing import NoReturn

import typer
from pydantic import BaseModel, ValidationError

from comx_harness.schemas.error_schemas import ErrorPayload
from comx_harness.shared.exceptions.harness_exceptions import HarnessError
from comx_harness.shared.exceptions.provider_exceptions import ProviderUnavailableError


def emit_model(model: BaseModel) -> None:
    typer.echo(model.model_dump_json(indent=2))


def fail_operation(error: Exception) -> NoReturn:
    if isinstance(error, HarnessError):
        code = error.code
    elif isinstance(error, ProviderUnavailableError):
        code = "provider_unavailable"
    elif isinstance(error, ValidationError):
        code = "validation_error"
    elif isinstance(error, (FileNotFoundError, KeyError)):
        code = "not_found"
    else:
        code = "operation_failed"
    payload = ErrorPayload(code=code, message=str(error) or error.__class__.__name__)
    typer.echo(payload.model_dump_json(indent=2), err=True)
    raise typer.Exit(code=2) from error
