import json
import os

import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def aws_credentials(scope="session", autouse=True):
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["LOG_LEVEL"] = "TRACE"


@mock_aws
def test_create_dynamodb_table():
    from predictive_capacity.upload import create_dynamodb_table

    table_name = "test_table"
    table = create_dynamodb_table(table_name)

    assert table.table_status == "ACTIVE"
    assert table.key_schema == [
        {"AttributeName": "class", "KeyType": "HASH"},
        {"AttributeName": "source#host_id#service_id", "KeyType": "RANGE"},
    ]
    assert table.global_secondary_indexes[0]["IndexName"] == "source-class-index"


@mock_aws
def test_create_s3_bucket():
    from predictive_capacity.upload import ML_RESULTS_BUCKET, create_s3_bucket

    s3 = boto3.client("s3")
    create_s3_bucket()
    bucket = s3.list_buckets()["Buckets"][0]

    assert bucket["Name"] == ML_RESULTS_BUCKET


@pytest.fixture
def metric_dict():
    return dict(
        metric_name="metric_name",
        days_to_full=1000,
        host_id="host_id",
        service_id="service_id",
        host_name="host_name",
        service_name="service_name",
        current_saturation=0.5,
        saturation_3_months=dict(current_saturation=0.5, forecast=0.7),
        saturation_6_months=dict(current_saturation=0.5, forecast=0.8),
        saturation_12_months=dict(current_saturation=0.5, forecast=0.9),
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


@mock_aws
def test_upload_prediction_metadata(metric_dict):
    from predictive_capacity.schemas import MetricBase
    from predictive_capacity.upload import (
        ML_RESULTS_TABLE,
        create_dynamodb_table,
        upload_prediction_metadata,
    )

    dynamodb = boto3.resource("dynamodb")
    create_dynamodb_table()

    metric = MetricBase.parse_obj(metric_dict)
    upload_prediction_metadata(source="source", metadata=metric)

    table = dynamodb.Table(ML_RESULTS_TABLE)
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


@mock_aws
def test_upload_prediction(metric_dict):
    from predictive_capacity.schemas import MetricBase
    from predictive_capacity.upload import ML_RESULTS_BUCKET, upload_prediction

    # Given
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket=ML_RESULTS_BUCKET)
    uuid = "uuid"

    # When
    metric = MetricBase.parse_obj(metric_dict)
    upload_prediction(metadata=metric)

    # Then
    response = s3.get_object(Bucket=ML_RESULTS_BUCKET, Key=f"{uuid}.json")
    data = json.loads(response["Body"].read().decode())
    assert data["data_scaled"] == [0.0, 0.1, 0.2]
    assert data["forecast"] == [0.3, 0.4, 0.5]


@mock_aws
def test_upload_all(metric_dict):
    from predictive_capacity.schemas import MetricBase
    from predictive_capacity.upload import (
        ML_RESULTS_BUCKET,
        ML_RESULTS_TABLE,
        create_dynamodb_table,
        upload_all,
    )

    # Given
    dynamodb = boto3.resource("dynamodb")
    s3 = boto3.client("s3", region_name="us-east-1")
    create_dynamodb_table()
    s3.create_bucket(Bucket=ML_RESULTS_BUCKET)

    # When
    metric = MetricBase.parse_obj(metric_dict)
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
