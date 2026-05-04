import pytest

from app.api.labels import filter_labels


@pytest.mark.parametrize(
    ("labels", "label_set", "expected"),
    [
        (
            {"name": "my-check", "namespace": "default"},
            ("name", "namespace"),
            {"name": "my-check", "namespace": "default"},
        ),
        (
            {"name": "my-check"},
            ("name", "namespace"),
            {"name": "my-check", "namespace": "unknown"},
        ),
        (
            {},
            ("name", "namespace"),
            {"name": "unknown", "namespace": "unknown"},
        ),
        (
            {"name": "my-check", "namespace": "default", "extra": "value"},
            ("name", "namespace"),
            {"name": "my-check", "namespace": "default"},
        ),
        (
            {"name": "my-check", "namespace": "default", "env": "prod"},
            ("name", "namespace", "env"),
            {"name": "my-check", "namespace": "default", "env": "prod"},
        ),
        (
            {},
            (),
            {},
        ),
    ],
)
def test_filter_labels(labels, label_set, expected):
    assert filter_labels(labels, label_set) == expected
