from typing import List

import boto3
import tqdm
from botocore.exceptions import ClientError
from loguru import logger

from predictive_capacity import (
    ML_RESULTS_BUCKET,
    ML_RESULTS_TABLE,
    ML_TRAINING_TIMEOUT,
    dynamodb,
    s3,
)
from predictive_capacity.forecast.metric import Metric
from predictive_capacity.schemas import ResponseFindSetMetrics
from predictive_capacity.upload import create_dynamodb_table, upload_all
from predictive_capacity.utils import get_uuid


def list_all_tables():
    dynamodb_client = dynamodb.meta.client

    table_names = []
    last_evaluated_table_name = None

    while True:
        if last_evaluated_table_name:
            response = dynamodb_client.list_tables(
                ExclusiveStartTableName=last_evaluated_table_name
            )
        else:
            response = dynamodb_client.list_tables()

        table_names.extend(response.get("TableNames", []))
        last_evaluated_table_name = response.get("LastEvaluatedTableName")

        if not last_evaluated_table_name:
            break

    return table_names


def bucket_exists(bucket_name):
    logger.debug(f"check if bucket {bucket_name} exists")
    try:
        s3_client = s3.meta.client
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        error_code = int(e.response["Error"]["Code"])
        if error_code == 404:
            return False
        else:
            logger.debug(f"Failed to check if bucket {bucket_name} exists: {e}")
        raise e


def make_forecasts(
    unique_labels: List[ResponseFindSetMetrics],
    read_token: str,
    organization: str,
    forecasting_horizon: int,
    timeout: int = ML_TRAINING_TIMEOUT,
):
    """
    Forecasts for all metrics in the database.

    Loop over all the metrics in the database and make forecasts for each of them.

    Parameters
    ----------
    unique_labels: List[ResponseFindSetMetrics]
        List of all the metrics in the database.
    read_token: str
        Token to read the metrics from Warp10.
    forecasting_horizon: int
        Number of days to forecast.
    source: str
        Source of the data.
    """

    # Ensure the bucket exists
    if not bucket_exists(ML_RESULTS_BUCKET):
        try:
            s3_client = s3.meta.client
            s3_client.create_bucket(Bucket=ML_RESULTS_BUCKET)
            logger.debug(f"Bucket {ML_RESULTS_BUCKET} created successfully.")
        except ClientError as e:
            logger.debug(f"Failed to create bucket {ML_RESULTS_BUCKET}: {e}")
            raise

    # Ensure the table exists
    logger.debug(f"Get list of dynamoDB tables")
    existing_tables = list_all_tables()
    logger.debug(f"tables: {existing_tables}")

    if ML_RESULTS_TABLE not in existing_tables:
        logger.error(f"Table {ML_RESULTS_TABLE} does not exist.")
        create_dynamodb_table(ML_RESULTS_TABLE)
        logger.debug(f"Table {ML_RESULTS_TABLE} created successfully.")

    for item in tqdm.tqdm(unique_labels):
        metric_name = item.metric
        host_id = item.host_id
        service_id = item.service_id
        platform_uuid = item.platform_uuid
        uuid = get_uuid(organization, metric_name, host_id, service_id)
        try:
            result = (
                Metric(
                    metric=metric_name,
                    host_id=host_id,
                    service_id=service_id,
                    platform_uuid=platform_uuid,
                    token=read_token,
                )
                .forecast(horizon=forecasting_horizon, timeout=timeout)
                .calculate_days_until_full()
                .to_dict(uuid=uuid)
            )
            upload_all(metric=result, source=organization)
        except Exception as e:
            logger.error(
                f"Something went wrong while making forecasts for key {item}: {e}"
            )
            break
