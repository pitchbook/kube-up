from prometheus_client import Counter

EXCEPTIONS = Counter(
    "http_exceptions_total",
    "Total number of exceptions raised by endpoint and exception type",
    ("method", "endpoint", "exception_type"),
)
