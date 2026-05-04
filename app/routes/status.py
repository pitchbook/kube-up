from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, RedirectResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

from app.api.metrics import update_metrics
from app.api.status import get_check_statuses
from app.routes.router import CustomRoute

status_router = APIRouter(route_class=CustomRoute)


@status_router.get("/", summary="Redirect to docs", include_in_schema=False)
async def get_ui() -> RedirectResponse:
    """
    Redirects root to /docs

    :return: 307
    """

    return RedirectResponse("/docs")


@status_router.get("/readyz", summary="Readiness check", description="Check if service is ready.")
async def get_healthcheck() -> Response:
    """
    Returns 200

    :return: HTTP 200
    """

    return Response()


@status_router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus metrics",
    description="Get service metrics in Prometheus format.",
)
async def get_metrics() -> Response:
    """
    Generates and returns Prometheus metrics

    :return: Prometheus metrics
    """

    *_, states = await get_check_statuses()
    update_metrics(states)

    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
