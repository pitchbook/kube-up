import time
from typing import TYPE_CHECKING

from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.routing import Match
from structlog import get_logger

from app.api.labels import filter_labels
from app.config import ALL_METRICS_LABELS, SETTINGS

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

    from app.models import SyntheticsState
    from app.models.synthetics_custom_metrics_labels import SyntheticCustomMetricLabel

REQUESTS = Counter(
    "http_requests_total", "Total number of HTTP requests by method and endpoint.", ("method", "endpoint")
)
RESPONSES = Counter(
    "http_responses_total",
    "Total number of HTTP responses by method, endpoint, status code.",
    ("method", "endpoint", "status"),
)
REQUESTS_PROCESSING_TIME = Histogram(
    "http_request_duration_seconds",
    "Request duration in seconds by method, endpoint, and status code",
    ("method", "endpoint", "status"),
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 20.0, 25.0, 30.0, 60.0, 90.0, 120.0, "+Inf"),
)
REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Gauge of requests by method and endpoint currently being processed",
    ("method", "endpoint"),
)
CHECK_METRICS = Gauge("kubeup_check", "Shows the status of a Kube Up check", ALL_METRICS_LABELS)
CHECK_DURATION_METRIC = Gauge(
    "kubeup_check_duration_seconds", "Shows the check run duration of a Kube Up check", ALL_METRICS_LABELS
)
CUSTOM_METRICS = {}

# Add one hit to ensure metrics available on service startup
REQUESTS.labels("GET", "/").inc()

logger = get_logger()


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware for Prometheus metrics logging
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Tabulate metrics, ignoring healthcheck, metrics, and docs endpoints

        :param request: request object
        :param call_next: next middleware
        :return: response object
        """

        method = request.method
        endpoint = self.get_path_template(request)

        # Skip metrics for ignored endpoints
        REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
        REQUESTS.labels(method=method, endpoint=endpoint).inc()

        try:
            before_time = time.time()
            response = await call_next(request)
            after_time = time.time()

            REQUESTS_PROCESSING_TIME.labels(method=method, endpoint=endpoint, status=response.status_code).observe(
                after_time - before_time
            )
            RESPONSES.labels(method=method, endpoint=endpoint, status=response.status_code).inc()
        finally:
            REQUESTS_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()

        return response

    @staticmethod
    def get_path_template(request: Request) -> str:
        """
        Get path from request

        :param request: request object
        :return: path
        """

        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return route.path

        return request.url.path


def _create_custom_metric(check_name: str, key: str, labels: list[SyntheticCustomMetricLabel]) -> Gauge:
    """
    Helper function for creating custom metrics

    :param key: Metric name
    :return: Prometheus Gauge
    """

    key = key.lower().replace("-", "_").replace(" ", "_")
    all_labels = set(ALL_METRICS_LABELS + tuple(label.name for label in labels))

    return Gauge(f"kubeup_check_custom_{key}", f"{key} metric for {check_name}", all_labels)


def update_metrics(states: list[SyntheticsState]) -> None:
    """
    Set Prometheus metrics

    :param states: KU States
    """

    # Reset all metrics in case a synthetic has been renamed or removed
    CHECK_METRICS.clear()
    CHECK_DURATION_METRIC.clear()
    for custom_metric in CUSTOM_METRICS.values():
        custom_metric.clear()

    for state in states:
        labels = {**filter_labels(state.labels.model_dump()), "name": state.name, "namespace": SETTINGS.namespace}
        CHECK_METRICS.labels(**labels).set(int(state.ok))
        CHECK_DURATION_METRIC.labels(**labels).set(state.run_duration_int)
        for custom_metric_obj in state.custom_metrics:
            try:
                custom_metric = CUSTOM_METRICS[custom_metric_obj.name]
            except KeyError:
                custom_metric = _create_custom_metric(state.name, custom_metric_obj.name, custom_metric_obj.labels)
                CUSTOM_METRICS[custom_metric_obj.name] = custom_metric
            custom_metric_labels = {**labels, **{label.name: label.value for label in custom_metric_obj.labels}}
            custom_metric.labels(**custom_metric_labels).set(custom_metric_obj.value)
