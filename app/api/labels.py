from typing import TYPE_CHECKING

from app.config import ALL_METRICS_LABELS

if TYPE_CHECKING:
    from collections.abc import Iterable


def filter_labels(labels: dict, label_set: Iterable = ALL_METRICS_LABELS) -> dict:
    """
    Filter out default Kubernetes labels and set default values for missing labels

    :param labels: labels
    :param label_set: label set to use for filtering
    :return: filtered labels
    """

    return {key: labels.get(key, "unknown") for key in label_set}
