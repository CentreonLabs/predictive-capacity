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

import os
from enum import Enum

import boto3
from loguru import logger


class Environment(Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


CURRENT_ENVIRONMENT = os.environ.get("CURRENT_ENVIRONMENT", Environment.DEVELOPMENT)

logger.info(f"Current environment: {CURRENT_ENVIRONMENT}")


# DEFAULTS
HORIZON_PREDICTION_HOURS = 365 * 24

ML_TRAINING_TIMEOUT = int(os.environ.get("ML_TRAINING_TIMEOUT", 600))

# Warp10
WARP10_SSL_VERIFY = os.getenv("WARP10_SSL_VERIFY", "F").lower() in ("true", "t", "1")

WARP10_READ_TOKEN = os.environ.get("WARP10_READ_TOKEN", "readTokenCI")
ML_WARP10_URL = os.environ.get("ML_WARP10_URL", "http://localhost")

# AWS
AWS_S3_ENDPOINT = os.environ.get("AWS_S3_ENDPOINT")
ML_RESULTS_TABLE = os.environ.get("ML_RESULTS_TABLE", "PredictiveCapacityResults")
ML_RESULTS_BUCKET = os.environ.get(
    "ML_RESULTS_BUCKET", "eu-west-1-ml-predictive-capacity-results"
)  # noqa: E501

# AWS
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "testing")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "testing")
AWS_SECURITY_TOKEN = os.environ.get("AWS_SECURITY_TOKEN", "testing")
AWS_SESSION_TOKEN = os.environ.get("AWS_SESSION_TOKEN", "testing")
AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

# DynamoDB
DYNAMODB_URL = os.environ.get("DYNAMODB_URL", "http://localhost:8000")
MINIO_URL = os.environ.get("MINIO_URL", "http://localhost:9000")

dynamodb = boto3.resource(
    "dynamodb",
    endpoint_url=DYNAMODB_URL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_DEFAULT_REGION,
)

s3 = boto3.resource(
    "s3",
    endpoint_url=MINIO_URL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_DEFAULT_REGION,
)


def __version__() -> str:
    with open("pyproject.toml") as f:
        text = f.readlines()
    return (
        [x for x in text if x.startswith("version")][0]
        .split("=")[1]
        .replace('"', "")
        .strip()
    )
