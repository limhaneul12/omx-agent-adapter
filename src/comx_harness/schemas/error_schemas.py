from typing import Literal

from comx_harness.schemas.common_schemas import NonEmptyString, StrictModel


class ErrorPayload(StrictModel):
    status: Literal["error"] = "error"
    code: NonEmptyString
    message: NonEmptyString
