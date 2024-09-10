# Copyright (C) 2024  Centreon
# This file is part of Predictive Capacity.
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
from decimal import Decimal

from loguru import logger
from mypy_boto3_dynamodb.service_resource import Table

from predictive_capacity import ML_RESULTS_BUCKET, ML_RESULTS_TABLE, dynamodb, s3
from predictive_capacity.schemas import MetricBase


def create_dynamodb_table(
    table_name: str = ML_RESULTS_TABLE,
) -> Table:
    """Function that creates a DynamoDB table if it does not exist.

    The table is created with the following parameters:
    - Partition key: "class" (string) - The class of the metric.
    - Sort key: "source#host_id#service_id" (string) - The source, host_id and
      service_id of the metric.
    - A global secondary index is created with the following parameters:
      - Partition key: "source" (string) - The name of the organisation.
      - Sort key: "uuid" (string) - The uuid used to retrieve the predictions in S3.
    - Attributes:
      - "host_name" (string) - The name of the host.
      - "service_name" (string) - The name of the service.
      - "days_to_full" (number) - The number of days until the metric is full.
      - "current_saturation" (number) - The current saturation of the metric.
      - "saturation_3_months" (map) - The saturation of the metric for the next 3 months.
      - "saturation_6_months" (map) - The saturation of the metric for the next 6 months.
      - "saturation_12_months" (map) - The saturation of the metric for the next 12 months.
      - "confidence_level" (number) - The confidence level of the prediction.

    Parameters
    ----------
    table_name : str
        Name of the DynamoDB table.
    """  # noqa E501
    logger.info(f"Creating table {table_name}...")
    try:
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "class", "KeyType": "HASH"},
                {"AttributeName": "source#host_id#service_id", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "class", "AttributeType": "S"},
                {"AttributeName": "source#host_id#service_id", "AttributeType": "S"},
                {"AttributeName": "source", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "source-class-index",
                    "KeySchema": [
                        {"AttributeName": "source", "KeyType": "HASH"},
                        {"AttributeName": "class", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        logger.info(f"Table {table_name} created successfully.")
        return dynamodb.Table(table_name)
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        logger.info(f"Table {table_name} already exists.")
        raise Exception(f"Table {table_name} already exists.")


def create_s3_bucket(bucket_name: str = ML_RESULTS_BUCKET) -> None:
    """Function that creates an S3 bucket if it does not exist."""
    logger.info(f"Creating bucket {bucket_name}...")

    try:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
        )
        logger.info(f"Bucket {bucket_name} created successfully.")
    except s3.meta.client.exceptions.BucketAlreadyOwnedByYou:
        logger.info(f"Bucket {bucket_name} already exists.")


def upload_prediction_metadata(
    source: str,
    metadata: MetricBase,
    table_name: str = ML_RESULTS_TABLE,
) -> None:
    """Upload metadata if it does not exist in DynamoDB.

    If the metadata exists, upload the attributes except for the uuid.
    If the metadata does not exist, it is uploaded to DynamoDB and a uuid.

    Returns the uuid of the metadata.
    """
    logger.info(f"Uploading metadata for {metadata.metric_name}...")

    table = dynamodb.Table(table_name)
    try:
        table.put_item(
            Item={
                "class": metadata.metric_name,
                "source#host_id#service_id": f"{source}#{metadata.host_id}#{metadata.service_id}",  # noqa E501
                "source": source,
                "uuid": metadata.uuid,
                "host_name": metadata.host_name,
                "service_name": metadata.service_name,
                "current_saturation": Decimal(str(metadata.current_saturation)),
                "saturation_3_months": {
                    k: Decimal(str(v))
                    for k, v in metadata.saturation_3_months.dict().items()  # noqa E501
                },
                "saturation_6_months": {
                    k: Decimal(str(v))
                    for k, v in metadata.saturation_6_months.dict().items()  # noqa E501
                },
                "saturation_12_months": {
                    k: Decimal(str(v))
                    for k, v in metadata.saturation_12_months.dict().items()  # noqa E501
                },
                "days_to_full": metadata.days_to_full,
                "confidence_level": metadata.confidence_level,
            }
        )
    except Exception as e:
        logger.error(f"error adding metadata item: {e}")

    logger.info(f"Metadata for {metadata.metric_name} uploaded successfully.")


def upload_prediction(
    metadata: MetricBase,
    bucket_name: str = ML_RESULTS_BUCKET,
) -> None:
    """Upload the prediction to S3.

    Predictions are stored in json format with the following structure:
    {
        "data_scaled": [0.0, 0.0, 0.0, ...],
        "data_dates": ["2021-01-01 00:00:00", "2021-01-01 01:00:00", ...],
        "forecast": [0.0, 0.0, 0.0, ...],
        "forecast_dates": ["2021-01-01 00:00:00", "2021-01-01 01:00:00", ...]
    }
    """
    logger.info(f"Uploading prediction for {metadata.uuid}...")

    bucket = s3.Bucket(bucket_name)
    body = json.dumps(
        {
            "data_scaled": metadata.data_scaled,
            "data_dates": metadata.data_dates,
            "forecast": metadata.forecast,
            "forecast_dates": metadata.forecast_dates,
        },
    )
    bucket.put_object(
        Body=body,
        Key=f"{metadata.uuid}.json",
    )
    logger.info(f"Prediction for {metadata.uuid} uploaded successfully.")


def upload_all(
    source: str,
    metric: MetricBase,
    table_name: str = ML_RESULTS_TABLE,
    bucket_name: str = ML_RESULTS_BUCKET,
) -> None:
    """Upload all the results to DynamoDB and S3."""
    try:
        upload_prediction_metadata(
            source=source,
            metadata=metric,
            table_name=table_name,
        )
    except Exception as e:
        logger.error(f"upload prediction metadata error: {e}")
        raise e

    try:
        upload_prediction(
            metadata=metric,
            bucket_name=bucket_name,
        )
    except Exception as e:
        logger.error(f"upload prediction error for uuid {metric.uuid}: {e}")
        raise e
