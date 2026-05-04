from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class AsyncAPIModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, alias_generator=to_camel)


class KubeUpBase(AsyncAPIModel):
    """
    Base model for Kube Up endpoints
    """

    # Aliases left for backwards compatibility, to be removed later in favor of camel case
    ok: bool = Field(True, description="Whether or not the check succeeded", examples=[True])
    errors: list[str] = Field([], description="List of errors encountered during check", examples=[[]])
