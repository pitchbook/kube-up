from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

if TYPE_CHECKING:
    from app.models import ErrorResponse


def generate_error_response(response_data: ErrorResponse, status_code: int = 500) -> JSONResponse:
    """
    Helper function for generating error responses

    :param response_data: response data
    :param status_code: HTTP status code
    :return: Response
    """

    return JSONResponse(response_data.model_dump(by_alias=True), status_code=status_code)
