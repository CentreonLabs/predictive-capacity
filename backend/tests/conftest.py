import os
from unittest.mock import patch

import pytest


@pytest.fixture
def aws_credentials(scope="session", autouse=True):
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["LOG_LEVEL"] = "TRACE"


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
