from pydantic import Field

from app.models._base import AsyncAPIModel
from app.models.synthetics_custom_metrics_labels import SyntheticCustomMetricLabel


class SyntheticCustomMetric(AsyncAPIModel):
    """
    Inner model for the POST /synthetics/results endpoint
    """

    name: str = Field(..., description="Metric name", examples=["ttfb"])
    value: int = Field(..., description="Metric value", examples=[5])
    labels: list[SyntheticCustomMetricLabel] = Field([], description="Metric label overrides")
