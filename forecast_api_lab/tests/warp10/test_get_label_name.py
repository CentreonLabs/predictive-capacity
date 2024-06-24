from unittest.mock import patch

import pytest

from predictive_capacity.warp10.get_label_name import get_label_name


@pytest.mark.parametrize(
    "labels, expected",
    [
        ({"service_name": ["service_name"]}, ("123", "service_name")),
        ({"host_name": ["host_name"]}, ("host_name", "123")),
        (
            {"host_name": ["host_name"], "service_name": ["service_name"]},
            ("host_name", "service_name"),
        ),
        ({}, ("123", "123")),
    ],
    ids=["service_name only", "host_name only", "both", "none"],
)
@patch("predictive_capacity.warp10.get_label_name.Warpscript.exec")
def test_get_label_name(mock_warpscript_exec, labels, expected):
    mock_warpscript_exec.return_value = (
        ["class1", "class2"],
        labels,
        {},
    )
    assert (
        get_label_name("token", "name", {"host_id": "123", "service_id": "123"})
        == expected
    )
