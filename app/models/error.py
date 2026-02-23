from pydantic import Field

from app.models._base import AsyncAPIModel


class ErrorResponse(AsyncAPIModel):
    """
    Response model for errors
    """

    message: str = Field(..., description="Error message", examples=["Unhandled exception in application"])
