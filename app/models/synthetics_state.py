from datetime import datetime

from pydantic import Field

from app.common.timestrs import timestr_to_seconds
from app.models._base import KubeUpBase
from app.models.synthetic_labels import SyntheticLabels
from app.models.synthetics_custom_metrics import SyntheticCustomMetric


class SyntheticsState(KubeUpBase):
    """
    Inner model for the GET /synthetics endpoint
    """

    name: str = Field(..., description="Name of Kube Up Check", examples=["test"])
    namespace: str = Field(..., description="Kubernetes namespace of check", examples=["monitoring"])
    last_run: datetime | None = Field(None, description="Timestamp of last check run")
    run_duration: str | None = Field(None, description="Duration of check run", examples=["10s"])
    authoritative_pod: str | None = Field(None, description="Name of last check pod", examples=["check"])
    labels: SyntheticLabels = Field(None, description="Extra metrics labels")
    custom_metrics: list[SyntheticCustomMetric] = Field([], description="Custom metrics")

    @property
    def run_duration_int(self):
        if self.run_duration is not None:
            return timestr_to_seconds(self.run_duration)
        return -1
