from unittest.mock import patch

import boto3
import matplotlib.pyplot as plt
import pandas as pd
import pytest
from moto import mock_dynamodb, mock_s3

from predictive_capacity.forecast.forecast import make_forecasts
from predictive_capacity.schemas import ResponseFindSetMetrics
from predictive_capacity.upload import (
    ML_RESULTS_BUCKET,
    ML_RESULTS_TABLE,
    create_dynamodb_table,
)


@pytest.fixture
def unique_labels():
    return ResponseFindSetMetrics(
        metric="#Passengers",
        host_id="123",
        service_id="123",
        platform_uuid="0000-0000-0000-0000",
        # source="centreon",
    )


def upload_all(metric, source):
    """Mock upload_gts function

    This function is used to mock the upload_gts function in the metric module.
    At this time, this function does nothing.

    TODO: Add forecast results and make sure forecast goes in the right direction.
    """
    metric_name = metric.metric_name
    data_scaled = metric.data_scaled
    data_dates = metric.data_dates
    forecast = metric.forecast
    forecast_dates = metric.forecast_dates
    metric = pd.DataFrame(
        {metric_name: data_scaled},
        index=pd.to_datetime(data_dates),
    )
    forecast = pd.DataFrame(
        {f"{metric_name}:forecast": forecast},
        index=pd.to_datetime(forecast_dates),
    )
    df = pd.concat([metric, forecast])
    df.plot()
    plt.savefig(f"tests/forecast/{metric_name}.png")


@patch("predictive_capacity.forecast.forecast.upload_all")
@patch("predictive_capacity.forecast.forecast.get_uuid", return_value="uuid")
@mock_s3
@mock_dynamodb
def test_make_forecast(
    mock_get_uuid,
    mock_upload_all,
    mock_metric,
    data,
    unique_labels,
):
    mock_upload_all.side_effect = upload_all
    mock_metric[1].return_value = data
    mock_metric[2].return_value = 1000
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=ML_RESULTS_BUCKET)
    dynamodb = boto3.resource("dynamodb")
    create_dynamodb_table(ML_RESULTS_TABLE)

    forecast = make_forecasts(
        # lower number will generate error from computing saturation_12_months
        forecasting_horizon=356 * 24,
        read_token="read",
        organization="firm",
        timeout=100,
        unique_labels=[unique_labels],
    )
    assert forecast is None
    for fun in mock_metric:
        fun.assert_called_once()
    mock_upload_all.assert_called_once()
    mock_get_uuid.assert_called_once()
    with patch("predictive_capacity.forecast.forecast.Metric") as mock_metric:
        mock_metric.side_effect = Exception("error")
        forecast = make_forecasts(
            forecasting_horizon=356 * 24,
            read_token="read",
            organization="firm",
            unique_labels=[unique_labels],
        )
        assert forecast is None
