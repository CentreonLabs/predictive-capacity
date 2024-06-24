import json
from unittest.mock import patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_s3

from predictive_capacity import ML_RESULTS_BUCKET
from predictive_capacity.api import app

client = TestClient(app)


def test_healthcheck():
    response = client.get("/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"healthcheck": "OK"}


DYNAMODB_ITEMS = [
    {
        "source#host_id#service_id": "source#1#1",
        "class": "metric1",
        "host_name": "host1",
        "service_name": "service1",
        "days_to_full": 1,
        "current_saturation": 1.0,
        "saturation_3_months": {"current_saturation": 1.0, "forecast": 0.0},
        "saturation_6_months": {"current_saturation": 1.0, "forecast": 0.0},
        "saturation_12_months": {"current_saturation": 1.0, "forecast": 0.0},
        "confidence_level": 0,
        "uuid": "00000000-0000-0000-0000-000000000000",
    },
]

DASHBOARD_EXPECTED = [
    {
        "host_id": "1",
        "service_id": "1",
        "metric_name": "metric1",
        "service_name": "service1",
        "host_name": "host1",
        "days_to_full": 1,
        "current_saturation": 1.0,
        "saturation_3_months": {"current_saturation": 1.0, "forecast": 0.0},
        "saturation_6_months": {"current_saturation": 1.0, "forecast": 0.0},
        "saturation_12_months": {"current_saturation": 1.0, "forecast": 0.0},
        "confidence_level": 0,
        "uuid": "00000000-0000-0000-0000-000000000000",
    },
]


@pytest.mark.parametrize(
    ids=["Returns 200", "Returns 404"],
    argnames=["status_code", "query", "expected"],
    argvalues=[
        (
            200,
            {
                "Count": 1,
                "Items": DYNAMODB_ITEMS,
            },
            DASHBOARD_EXPECTED,
        ),
        (404, {"Count": 0, "Items": []}, {"detail": "No dashboard found"}),
    ],
)
@patch("predictive_capacity.api.table.query")
@patch("predictive_capacity.api.boto3.resource")
def test_read_dashboard(
    mock_query,
    status_code,
    query,
    expected,
):
    mock_query.return_value = query
    result = client.get("/metrics")
    assert result.status_code == status_code
    assert result.json() == expected


S3_OBJECT = {
    "data_scaled": [1, 2, 3],
    "data_dates": ["2021-01-01", "2021-01-02", "2021-01-03"],
    "forecast": [4, 5, 6],
    "forecast_dates": ["2021-01-04", "2021-01-05", "2021-01-06"],
}


@pytest.mark.parametrize(
    ids=["Success", "No such key"],
    argnames=["status_code", "uuid", "detail"],
    argvalues=[
        (200, "test_uuid", S3_OBJECT),
        (404, "wrong_uuid", {"detail": "No prediction found"}),
    ],
)
@mock_s3
@patch("predictive_capacity.api.boto3.client")
def test_read_predictions(status_code, uuid, detail):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=ML_RESULTS_BUCKET)
    s3.put_object(
        Bucket=ML_RESULTS_BUCKET, Key="test_uuid.json", Body=json.dumps(S3_OBJECT)
    )
    result = client.get(f"/predictions/{uuid}")
    assert result.status_code == status_code
    assert result.json() == detail


@pytest.mark.parametrize(
    "set_metrics, status, expected",
    [
        ("failure", 500, "Failed to get Warp10 data with error Failure"),
        ("find_set_metrics_empty", 404, "No metrics found"),
        ("find_set_metrics", 202, None),
    ],
    ids=["warp10_error", "no_metrics", "metrics"],
)
@patch("predictive_capacity.api.make_forecasts")
@patch("predictive_capacity.api.find_set_metrics")
def test_forecast(
    mock_find_set_metrics,
    mock_make_forecasts,
    set_metrics,
    status,
    expected,
    request,
):
    mock_find_set_metrics.side_effect = lambda *args, **kwargs: request.getfixturevalue(
        set_metrics
    )
    response = client.post("/forecast")
    assert response.status_code == status
    if status == 202:
        assert mock_make_forecasts.called
        assert response.text == ""
    else:
        assert response.text == f'{{"detail":"{expected}"}}'
