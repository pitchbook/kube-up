from pydantic import Field

from app.models._base import AsyncAPIModel


class SyntheticCustomMetricLabel(AsyncAPIModel):
    """
    Inner model for the POST /synthetics/results endpoint's custom metrics
    """

    name: str = Field(..., description="Label name", examples=["service"])
    value: str = Field(..., description="Label value", examples=["authentication-service"])
