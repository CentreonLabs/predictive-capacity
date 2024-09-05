import json
from decimal import Decimal
from unittest.mock import patch

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws


@pytest.fixture
@mock_aws
def client(scope="session") -> TestClient:
    from predictive_capacity.api import app

    return TestClient(app)


def test_healthcheck(client):
    response = client.get("/healthcheck")
    assert response.status_code == 200
    assert response.json() == {"healthcheck": "OK"}


DYNAMODB_ITEM = {
    "source": "test",
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
}


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
    ids=["Success", "Missing data"],
    argnames=["status_code", "items", "expected"],
    argvalues=[
        (200, [DYNAMODB_ITEM], DASHBOARD_EXPECTED),
        (404, [], {"detail": "No dashboard found"}),
    ],
)
@mock_aws
def test_read_dashboard(status_code: int, items: dict, expected: dict, client):
    from predictive_capacity.upload import ML_RESULTS_TABLE, create_dynamodb_table

    create_dynamodb_table(ML_RESULTS_TABLE)
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(ML_RESULTS_TABLE)
    for item in items:
        table.put_item(Item=json.loads(json.dumps(item), parse_float=Decimal))
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
@mock_aws
def test_read_predictions(status_code: int, uuid: str, detail: dict, client):
    from predictive_capacity.upload import ML_RESULTS_BUCKET, create_s3_bucket

    create_s3_bucket(ML_RESULTS_BUCKET)
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=ML_RESULTS_BUCKET, Key="test_uuid.json", Body=json.dumps(S3_OBJECT)
    )
    result = client.get(f"/predictions/{uuid}")
    assert result.status_code == status_code
    assert result.json() == detail


@pytest.fixture
def dict_metric() -> dict:
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
    return response


@pytest.fixture
def failure(*args, **kwargs):
    raise Exception("Failure")


@pytest.fixture
def find_set_metrics_empty():
    yield []


@pytest.fixture
def find_set_metrics(dict_metric):
    yield [dict_metric]


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
@mock_aws
def test_forecast(
    mock_find_set_metrics,
    mock_make_forecasts,
    set_metrics,
    status,
    expected,
    request,
    client,
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
