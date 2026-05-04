import pytest

from app.common.timestrs import timestr_to_minutes, timestr_to_seconds


@pytest.mark.parametrize(
    ("timestr", "expected"),
    [
        ("30s", 30),
        ("1s", 1),
        ("0s", 0),
        ("90s", 90),
        ("1m", 60),
        ("5m", 300),
        ("30m", 1800),
        ("1h", 3600),
        ("2h", 7200),
        ("0.5h", 1800),
    ],
)
def test_timestr_to_seconds(timestr, expected):
    assert timestr_to_seconds(timestr) == expected


@pytest.mark.parametrize(
    "timestr",
    ["1d", "1w", "1", "", "bad"],
)
def test_timestr_to_seconds_unsupported(timestr):
    with pytest.raises(ValueError, match="Unsupported time string"):
        timestr_to_seconds(timestr)


def test_timestr_to_seconds_ambiguous_suffix():
    # "1ms" ends with "s" so it tries to parse "1m" as float, raising ValueError from the float conversion rather than
    # the unsupported-suffix branch.
    with pytest.raises(ValueError):  # noqa: PT011
        timestr_to_seconds("1ms")


@pytest.mark.parametrize(
    ("timestr", "expected"),
    [
        ("60s", "1"),
        ("120s", "2"),
        ("30s", "0"),
        ("1m", "1"),
        ("5m", "5"),
        ("1h", "60"),
        ("2h", "120"),
    ],
)
def test_timestr_to_minutes(timestr, expected):
    assert timestr_to_minutes(timestr) == expected
