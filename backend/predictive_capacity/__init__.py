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

import boto3
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
from mypy_boto3_s3.service_resource import S3ServiceResource

# DEFAULTS
HORIZON_PREDICTION_HOURS = 365 * 24

ML_TRAINING_TIMEOUT = int(os.environ.get("ML_TRAINING_TIMEOUT", 600))

# Warp10
WARP10_SSL_VERIFY = os.getenv("WARP10_SSL_VERIFY", "F").lower() in ("true", "t", "1")

WARP10_READ_TOKEN = os.environ.get("WARP10_READ_TOKEN", "readTokenCI")
ML_WARP10_URL = os.environ.get("ML_WARP10_URL", "http://localhost")

# AWS
ML_RESULTS_TABLE = os.environ.get("ML_RESULTS_TABLE", "PredictiveCapacityResults")
ML_RESULTS_BUCKET = os.environ.get(
    "ML_RESULTS_BUCKET", "eu-west-1-ml-predictive-capacity-results"
)

dynamodb: DynamoDBServiceResource = boto3.resource("dynamodb")
s3: S3ServiceResource = boto3.resource("s3")


def __version__() -> str:
    with open("pyproject.toml") as f:
        text = f.readlines()
    return (
        [x for x in text if x.startswith("version")][0]
        .split("=")[1]
        .replace('"', "")
        .strip()
    )
