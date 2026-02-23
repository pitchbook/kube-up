from fastapi import APIRouter, Request, Response
from structlog import get_logger

from app.api.responses import generate_error_response
from app.api.status import get_check_statuses, update_state
from app.models import ErrorResponse, KUNotFoundError, ResultsRequest, SyntheticsResponse
from app.routes.router import CustomRoute

logger = get_logger()

kube_up_router = APIRouter(route_class=CustomRoute)


@kube_up_router.get(
    "/synthetics",
    response_model=SyntheticsResponse,
    summary="Retrieve status of all checks",
    description="Retrieves the status of all Kube Up synthetic checks.",
)
async def get_synthetics():
    """
    Retrieve status of all checks

    :return: Check states
    """

    overall_status, all_errors, states = await get_check_statuses()

    return SyntheticsResponse(ok=overall_status, errors=all_errors, check_details=states)


@kube_up_router.post(
    "/synthetics/results",
    status_code=201,
    summary="Submit results from a synthetic run",
    description="Submits the results and metrics from a synthetic run.",
)
async def post_results(results_request: ResultsRequest, request: Request):
    """
    Submit results from a synthetic run

    :param results_request: request payload
    :param request: request object (used to retrieve IP)
    :return: response
    """

    try:
        # If pod name not included in request, fall back to retrieving pod name from IP
        if results_request.pod_name:
            await results_request.get_pod_details_from_name()
        else:
            client_host = request.client.host if request.client else "unknown"
            await results_request.get_pod_details_from_ip(request.headers.get("X-Forwarded-For", client_host))
        await update_state(results_request)
    except KUNotFoundError as ex:
        return generate_error_response(ErrorResponse(message=str(ex)), status_code=404)
    else:
        return Response(status_code=201)
