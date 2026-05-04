import importlib.metadata
import os
from contextlib import asynccontextmanager

import kubernetes_asyncio
import uvicorn
from fastapi import FastAPI
from structlog import get_logger

from app.api.metrics import PrometheusMiddleware
from app.common.client import API_CLIENT
from app.config import SETTINGS
from app.models import ErrorResponse
from app.routes import kube_up_router, status_router

logger = get_logger()


@asynccontextmanager
async def lifespan(*args, **kwargs):
    # Startup
    if "KUBERNETES_PORT" in os.environ:
        logger.debug("using in-cluster config")
        kubernetes_asyncio.config.load_incluster_config()
    else:
        logger.debug("using local config")
        await kubernetes_asyncio.config.load_kube_config()
    await API_CLIENT.load()

    # Main loop
    yield


application = FastAPI(
    title="Kube Up API",
    description="API for the Kube Up operator",
    version=importlib.metadata.version("kube-up"),
    docs_url="/docs",
    openapi_url="/api/v1/openapi.json",
    swagger_ui_parameters={"syntaxHighlight": False},
    strict_content_type=False,
    lifespan=lifespan,
)
application.include_router(
    kube_up_router, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}, tags=["Kube-Up"]
)
application.include_router(
    status_router, responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}, tags=["Status"]
)
application.add_middleware(PrometheusMiddleware)  # type: ignore[arg-type]

if __name__ == "__main__":
    uvicorn.run(
        application,
        host=SETTINGS.host_address,
        port=SETTINGS.host_port,
        log_config=None,
        access_log=False,
        timeout_keep_alive=SETTINGS.timeout,
    )
