from unittest.mock import patch

import matplotlib.pyplot as plt
import pandas as pd
import pytest


def upload_all(metric, source):
    """Mock upload_gts function

    This function is used to mock the upload_gts function in the metric module.
    At this time, this function does nothing.

    TODO: Add forecast results and make sure forecast goes in the right direction.
    """
    from predictive_capacity import __version__

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
    plt.savefig(f"tests/forecast/{metric_name}_{__version__}.png")


@pytest.fixture
def data():
    """Load data from AirPassengers.csv

    This fixture is use to test the forecast function.
    """
    df = pd.read_csv("tests/forecast/AirPassengers.csv", parse_dates=True, usecols=[1])
    df.index = pd.date_range(start="2023-04-01", periods=len(df), freq="1d")
    return df


@patch("predictive_capacity.forecast.forecast.s3")
@patch("predictive_capacity.forecast.forecast.bucket_exists", return_value=False)
@patch("predictive_capacity.forecast.forecast.list_all_tables")
@patch("predictive_capacity.forecast.forecast.create_dynamodb_table")
@patch(
    "predictive_capacity.forecast.metric.get_label_name",
    return_value=("host", "service"),
)
@patch("predictive_capacity.forecast.metric.fetch_metric")
@patch("predictive_capacity.forecast.metric.get_metric_saturation", return_value=1000)
@patch("predictive_capacity.forecast.forecast.upload_all")
@patch("predictive_capacity.forecast.forecast.get_uuid", return_value="uuid")
def test_make_forecast(
    mock_get_uuid,
    mock_upload_all,
    mock_get_metric_saturation,
    mock_fetch_metric,
    mock_get_label_name,
    mock_create_dynamodb_table,
    mock_list_all_tables,
    mock_bucket_exists,
    mock_s3,
    data,
):
    from predictive_capacity.forecast.forecast import (
        make_forecasts,
        ResponseFindSetMetrics,
    )

    mock_fetch_metric.return_value = data
    mock_upload_all.side_effect = upload_all

    unique_labels = ResponseFindSetMetrics(
        metric="#Passengers",
        host_id="123",
        service_id="123",
        platform_uuid="0000-0000-0000-0000",
        # source="centreon",
    )

    forecast = make_forecasts(
        # lower number will generate error from computing saturation_12_months
        forecasting_horizon=356 * 24,
        read_token="read",
        organization="firm",
        timeout=100,
        unique_labels=[unique_labels],
    )
    assert forecast is None
    mock_get_label_name.assert_called_once()
    mock_fetch_metric.assert_called_once()
    mock_get_metric_saturation.assert_called_once()
    mock_create_dynamodb_table.assert_called_once()
    mock_list_all_tables.assert_called_once()
    mock_bucket_exists.assert_called_once()
    mock_s3.meta.client.create_bucket.assert_called_once()
    mock_upload_all.assert_called_once()
    mock_get_uuid.assert_called_once()
