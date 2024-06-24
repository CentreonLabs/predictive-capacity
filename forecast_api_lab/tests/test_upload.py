import json
from unittest.mock import patch

import boto3
import pytest
from moto import mock_dynamodb, mock_s3

from predictive_capacity.schemas import MetricBase, SaturationForecast
from predictive_capacity.upload import (
    ML_RESULTS_BUCKET,
    ML_RESULTS_TABLE,
    create_dynamodb_table,
    create_s3_bucket,
    upload_all,
    upload_prediction,
    upload_prediction_metadata,
)


@mock_dynamodb
def test_create_dynamodb_table():
    # Given
    dynamodb = boto3.resource("dynamodb")

    # When
    create_dynamodb_table()

    # Then
    table = dynamodb.Table(ML_RESULTS_TABLE)  # type: ignore
    assert table.table_status == "ACTIVE"
    assert table.key_schema == [
        {"AttributeName": "class", "KeyType": "HASH"},
        {"AttributeName": "source#host_id#service_id", "KeyType": "RANGE"},
    ]
    assert table.global_secondary_indexes[0]["IndexName"] == "source-class-index"


@mock_s3
def test_create_s3_bucket():
    # Given
    s3 = boto3.resource("s3", region_name="us-east-1")

    # When
    create_s3_bucket()

    # Then
    bucket = s3.Bucket(ML_RESULTS_BUCKET)  # type: ignore
    assert bucket.name == ML_RESULTS_BUCKET


@pytest.fixture
def metric():
    return MetricBase(
        metric_name="metric_name",
        days_to_full=1000,
        host_id="host_id",
        service_id="service_id",
        host_name="host_name",
        service_name="service_name",
        current_saturation=0.5,
        saturation_3_months=SaturationForecast(current_saturation=0.5, forecast=0.7),
        saturation_6_months=SaturationForecast(current_saturation=0.5, forecast=0.8),
        saturation_12_months=SaturationForecast(current_saturation=0.5, forecast=0.9),
        uuid="uuid",
        confidence_level=50,
        data_scaled=[0.0, 0.1, 0.2],
        data_dates=[
            "2021-01-01 00:00:00",
            "2021-01-01 01:00:00",
            "2021-01-01 02:00:00",
        ],
        forecast=[0.3, 0.4, 0.5],
        forecast_dates=[
            "2021-01-02 00:00:00",
            "2021-01-02 01:00:00",
            "2021-01-02 02:00:00",
        ],
    )


@mock_dynamodb
def test_upload_prediction_metadata(metric):
    dynamodb = boto3.resource("dynamodb")
    create_dynamodb_table()

    upload_prediction_metadata(source="source", metadata=metric)

    table = dynamodb.Table(ML_RESULTS_TABLE)  # type: ignore
    response = table.get_item(
        Key={
            "class": "metric_name",
            "source#host_id#service_id": "source#host_id#service_id",
        }
    )
    assert "Item" in response
    assert response["Item"]["uuid"] == "uuid"
    upload_prediction_metadata(source="source", metadata=metric)
    number_of_items = table.scan()["Count"]
    assert number_of_items == 1


@mock_s3
def test_upload_prediction(metric):
    # Given
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=ML_RESULTS_BUCKET)
    uuid = "uuid"

    # When
    upload_prediction(metadata=metric)

    # Then
    response = s3.get_object(Bucket=ML_RESULTS_BUCKET, Key=f"{uuid}.json")
    data = json.loads(response["Body"].read().decode())
    assert data["data_scaled"] == [0.0, 0.1, 0.2]
    assert data["forecast"] == [0.3, 0.4, 0.5]


@mock_dynamodb
@mock_s3
def test_upload_all(metric):
    # Given
    dynamodb = boto3.resource("dynamodb")
    s3 = boto3.client("s3", region_name="us-east-1")
    create_dynamodb_table()
    s3.create_bucket(Bucket=ML_RESULTS_BUCKET)

    # When
    upload_all(source="source", metric=metric)

    # Then
    table = dynamodb.Table(ML_RESULTS_TABLE)
    # type: ignore
    response = table.get_item(
        Key={
            "class": "metric_name",
            "source#host_id#service_id": "source#host_id#service_id",
        }
    )
    assert "Item" in response
    uuid = response["Item"]["uuid"]

    response = s3.get_object(Bucket=ML_RESULTS_BUCKET, Key=f"{uuid}.json")
    data = json.loads(response["Body"].read().decode())
    assert data["data_scaled"] == [0.0, 0.1, 0.2]
    assert data["forecast"] == [0.3, 0.4, 0.5]
