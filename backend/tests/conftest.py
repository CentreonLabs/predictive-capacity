from typing import Any, Generator
from unittest.mock import patch

import pandas as pd
import pytest

from predictive_capacity.schemas import MetricBase


@pytest.fixture
def data() -> Generator[pd.DataFrame, Any, Any]:
    """Load data from AirPassengers.csv

    This fixture is use to test the forecast function.
    """
    df = pd.read_csv("tests/forecast/AirPassengers.csv", parse_dates=True, usecols=[1])
    df.index = pd.date_range(start="2023-04-01", periods=len(df), freq="1d")
    yield df


@pytest.fixture
def mock_metric():
    """Mock the Metric class

    This fixture is used to mock the Metric class in the forecast module.
    All functions that are called which deal with warp10 database are mocked.
    """
    with (
        patch(
            "predictive_capacity.forecast.metric.get_label_name"
        ) as mock_get_label_name,
        patch("predictive_capacity.forecast.metric.fetch_metric") as mock_fetch_metric,
        patch(
            "predictive_capacity.forecast.metric.get_metric_saturation"
        ) as mock_get_metric_saturation,
    ):
        mock_get_label_name.return_value = ("host_name", "service_name")
        yield (
            mock_get_label_name,
            mock_fetch_metric,
            mock_get_metric_saturation,
        )


@pytest.fixture
def dict_metric() -> Generator[dict, Any, Any]:
    """Create a fake response to retrieve forecast

    Since we use BaseModel to validate the response, we need to ensure that the
    response is valid. Unfortunately, we cannot use the MetricBase as a yield"""
    response = {
        "metric_name": "test:forecast",
        "host_name": "host_name",
        "host_id": "123",
        "service_id": "123",
        "service_name": "service_name",
        "data_scaled": [],
        "data_dates": [],
        "forecast": [],
        "forecast_dates": [],
        "days_to_full": None,
        "current_saturation": 0.0,
        "saturation_3_months": {"current_saturation": 0.0, "forecast": 0.0},
        "saturation_6_months": {"current_saturation": 0.0, "forecast": 0.0},
        "saturation_12_months": {"current_saturation": 0.0, "forecast": 0.0},
        "confidence_level": 0,
        "uuid": "00000000-0000-0000-0000-000000000000",
    }
    MetricBase(**response)
    yield response


@pytest.fixture
def failure(*args, **kwargs):
    raise Exception("Failure")


@pytest.fixture
def find_set_metrics_empty():
    yield []


@pytest.fixture
def find_set_metrics(dict_metric):
    yield [dict_metric]
