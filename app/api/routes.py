from copy import copy
from typing import TYPE_CHECKING

import orjson
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException
from structlog import get_logger
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.api.responses import generate_error_response
from app.common.logs import get_new_request_id, log_exception
from app.common.metrics import EXCEPTIONS
from app.config import SETTINGS
from app.models import ErrorResponse

if TYPE_CHECKING:
    from collections.abc import Callable

    from starlette.requests import Request
    from starlette.responses import Response

REQUEST_LOGGING = SETTINGS.log_level.lower() == "debug"
MAX_LOG_LENGTH = 1000000
IGNORED_ROUTES = {"/readyz", "/metrics"}


async def _get_request_data(request: Request) -> str | None:
    """
    Get JSON request data (if applicable) as a string

    :param request: Request object
    :return: request data string
    """

    if "application/json" in request.headers.get("content-type", "").lower():
        try:
            request_data = copy(await request.json())
            if "password" in request_data:
                request_data["password"] = "********"
            request_data = str(request_data)[:MAX_LOG_LENGTH]
        except Exception:
            request_data = "error retrieving JSON"
    else:
        request_data = None

    return request_data


def get_logging_route(application_name: str) -> type[APIRoute]:
    """
    Closure for setting request/response logging in custom APIRoute class

    :param application_name: name of microservice
    :return: logging APIRoute class
    """

    class LoggingRoute(APIRoute):
        """
        Custom APIRoute for logging requests and responses and attaching relevant request data to logger
        """

        def get_route_handler(self) -> Callable:
            """
            Get custom route handler

            :return: custom route handler
            """

            original_route_handler = super().get_route_handler()

            async def custom_route_handler(request: Request) -> Response:
                """
                Handle route and logging

                :param request: Application request
                :return: Response
                """

                # Set request metadata for logging
                request_id = get_new_request_id()

                path_variables = copy(request.path_params)
                # Remove filename key to prevent it from sticking around
                path_variables.pop("filename", None)
                query_parameters = request.query_params

                clear_contextvars()
                bind_contextvars(
                    requestId=request_id,
                    requestMethod=request.method,
                    requestPath=request.url.path,
                    remoteIPAddress=request.headers.get(
                        "X-Forwarded-For", request.client.host if request.client else None
                    ),
                    **path_variables,
                    **query_parameters,
                )
                logger = get_logger("application")

                if REQUEST_LOGGING and request.url.path.rstrip("/") not in IGNORED_ROUTES:
                    logger.debug(f"{application_name} request", applicationRequest=await _get_request_data(request))

                try:
                    response: Response = await original_route_handler(request)
                except RequestValidationError as ex:
                    log_exception(
                        ex, "Validation error", logger=logger, applicationRequest=await _get_request_data(request)
                    )
                    response = generate_error_response(ErrorResponse(message=str(ex.errors())), 400)
                except HTTPException as ex:
                    response = generate_error_response(ErrorResponse(message=ex.detail), ex.status_code)
                except Exception as ex:
                    # Handle JSON parsing errors
                    if isinstance(ex, HTTPException) and getattr(ex, "status_code", None) == 400:
                        status_code = 400
                        message = "Request body is not valid JSON"
                    else:
                        log_exception(
                            ex,
                            logger=logger,
                            applicationRequest=await _get_request_data(request),
                            **request.state._state,
                        )
                        EXCEPTIONS.labels(
                            method=request.method, endpoint=request.url.path, exception_type=type(ex).__name__
                        ).inc()
                        status_code = 500
                        message = f"Unhandled exception in application: {type(ex).__name__}({ex})"
                    response = generate_error_response(ErrorResponse(message=message), status_code)

                if REQUEST_LOGGING and request.url.path.rstrip("/") not in IGNORED_ROUTES:
                    if response.media_type == "application/json":
                        response_data = str(orjson.loads(response.body))[:MAX_LOG_LENGTH]
                    else:
                        response_data = str(response.body)[:MAX_LOG_LENGTH] if response.body else None
                    logger.debug(
                        f"{application_name} response",
                        statusCode=response.status_code,
                        applicationResponse=response_data,
                    )

                clear_contextvars()

                return response

            return custom_route_handler

    return LoggingRoute
