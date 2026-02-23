from pydantic import Field

from app.models._base import KubeUpBase
from app.models.synthetics_state import SyntheticsState


class SyntheticsResponse(KubeUpBase):
    """
    Response model for the GET /synthetics endpoint
    """

    check_details: list[SyntheticsState] = Field(..., description="List of errors encountered during check")
