from pydantic import BaseModel, ConfigDict


class AdapterSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
