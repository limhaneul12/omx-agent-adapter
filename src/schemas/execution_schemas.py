from typing import Annotated

from pydantic import StringConstraints

from schemas.common_schemas import AdapterSchema

NonEmptyString = Annotated[str, StringConstraints(min_length=1)]


class ExecRequest(AdapterSchema):
    prompt: NonEmptyString
    cwd: str | None = None


class ExecMessage(AdapterSchema):
    kind: str
    text: str
