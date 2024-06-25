import pandas as pd
import pytest

from predictive_capacity.warp10.utils import build_gts_input_format


@pytest.mark.parametrize(
    "timestamp, value, expected, error",
    [
        ([], [], "Timestamp cannot be empty.", True),
        (1, 1.0, "1// test{label=value} 1.0\n", False),
        (1, [1.0, 2.0], "1// test{label=value} '[1.0, 2.0]'\n", False),
        ([1, 2], [1], "Timestamp and value must have the same length.", True),
        (1.0, 1.0, "Timestamp must be a string, int or pd.Timestamp.", True),
        (
            "2021-01-01 00:00:00",
            1.0,
            "1609459200000000// test{label=value} 1.0\n",
            False,
        ),
        (
            pd.Timestamp("2021-01-01 00:00:00"),
            1.0,
            "1609459200000000// test{label=value} 1.0\n",
            False,
        ),
        (
            ["2021-01-01 00:00:00", "2021-01-01 01:00:00"],
            [1.0, 2.0],
            "1609459200000000// test{label=value} 1.0\n=1609462800000000// 2.0\n",
            False,
        ),
    ],
)
def test_build_warp10_metric(timestamp, value, expected, error):
    if error:
        with pytest.raises(ValueError) as e:
            build_gts_input_format("test", {"label": "value"}, value, timestamp)
        assert str(e.value) == expected
    else:
        assert (
            build_gts_input_format("test", {"label": "value"}, value, timestamp)
            == expected
        )
