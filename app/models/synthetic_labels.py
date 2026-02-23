from typing import Any

from pydantic import create_model

from app.config import SETTINGS
from app.models._base import AsyncAPIModel

# Inner model for the GET /synthetics endpoint
# Defined dynamically from config
SyntheticLabels = create_model(  # type: ignore[call-overload]
    "SyntheticLabels", **{field: (Any, field) for field in SETTINGS.extra_metrics_labels}, __base__=(AsyncAPIModel,)
)
