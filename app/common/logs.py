import logging
import sys
import uuid
from logging import config as logging_config
from typing import TYPE_CHECKING

import orjson
import structlog
from structlog import get_logger
from structlog.processors import CallsiteParameter

from app.common.metrics import EXCEPTIONS

if TYPE_CHECKING:
    from collections.abc import Callable

LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

PACKAGE_LOG_LEVELS = {
    "fontTools.subset": logging.ERROR,
    "fontTools.ttLib.ttFont": logging.ERROR,
    "matplotlib": logging.ERROR,
    "PIL": logging.ERROR,
    "tortoise": logging.ERROR,
    "urllib3": logging.ERROR,
}

logger = get_logger()


def _dumps(event_dict: dict, default: Callable | None = None) -> bytes:
    """
    Custom dumps function to order log fields and use orjson for serialization

    :param event_dict: log event dict
    :param default: default function for orjson
    :return: serialized log entry as bytes
    """

    return orjson.dumps(
        {
            "timestamp": event_dict.pop("timestamp"),
            "level": event_dict.pop("level"),
            "message": event_dict.pop("event"),
            **event_dict,
        },
        default,
    )


def get_new_request_id() -> str:
    """
    Get a new UUID string for a request

    :return: UUID string
    """

    return str(uuid.uuid4()).replace("-", "")


def log_exception(
    ex: Exception,
    message: str = "Unhandled exception",
    logger: structlog.BoundLogger | None = None,
    **kwargs,
):
    """
    Log an exception with a traceback

    :param ex: Exception
    :param message: optional message
    :param logger: logger, if needed to surface bound kwargs
    :param kwargs: additional fields for log entry
    """

    if logger is None:
        logger = structlog.get_logger()
    logger.exception(message, exceptionType=type(ex).__name__, exceptionMessage=str(ex), exc_info=True, **kwargs)


def setup_logging(level: str = "info", package_overrides: dict | None = None) -> None:
    """
    Setup Structlog

    :param level: log level
    :param package_overrides: dict mapping package name to log level.
    """

    config_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "pythonjsonlogger.orjson.OrjsonFormatter",
                "fmt": "%(asctime)s %(levelname)s %(message)s %(pathname)s %(lineno)d",
                "datefmt": "%Y-%m-%dT%H:%M:%S",
                "rename_fields": {"asctime": "timestamp", "levelname": "level"},
            }
        },
        "handlers": {
            "json": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            }
        },
        "loggers": {
            "": {"handlers": ["json"]},
        },
    }
    logging_config.dictConfig(config_dict)

    structlog.configure(
        logger_factory=structlog.BytesLoggerFactory(file=sys.stderr.buffer),
        wrapper_class=structlog.make_filtering_bound_logger(LOG_LEVELS[level.lower()]),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.CallsiteParameterAdder(
                parameters={CallsiteParameter.PATHNAME, CallsiteParameter.LINENO}
            ),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.ExceptionRenderer(),
            structlog.processors.JSONRenderer(serializer=_dumps),
        ],
        cache_logger_on_first_use=True,
    )

    # Override log levels for specific packages
    if package_overrides:
        PACKAGE_LOG_LEVELS.update(package_overrides)

    for package, pkg_level in PACKAGE_LOG_LEVELS.items():
        try:
            if isinstance(pkg_level, str):
                log_level: int = LOG_LEVELS[pkg_level.lower().strip()]
            else:
                log_level = pkg_level
            logging.getLogger(package).setLevel(log_level)
        except Exception as ex:
            log_exception(ex, "failed to set log level")


def log_unhandled_exceptions(
    ex: Exception, method: str, function: str, message: str = "Unhandled exception", **kwargs
) -> None:
    """
    Log unhandled exceptions as Prometheus metrics

    :param ex: exception
    :param method: HTTP method
    :param function: function name
    :param message: exception message
    :param kwargs: additional fields for log entry
    """

    log_exception(ex, message, logger, **kwargs)
    EXCEPTIONS.labels(method=method, endpoint=function, exception_type=type(ex).__name__).inc()
