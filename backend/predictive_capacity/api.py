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
import sys

import botocore.exceptions
from boto3.dynamodb import conditions
from fastapi import BackgroundTasks, FastAPI, HTTPException, Response, status
from loguru import logger
from starlette.middleware.cors import CORSMiddleware

import predictive_capacity.schemas as schemas
from predictive_capacity import (
    HORIZON_PREDICTION_HOURS,
    ML_RESULTS_BUCKET,
    ML_RESULTS_TABLE,
    WARP10_READ_TOKEN,
    __version__,
    dynamodb,
    s3,
)
from predictive_capacity.forecast.forecast import make_forecasts
from predictive_capacity.utils import JSONEcoder
from predictive_capacity.warp10.find_set_metrics import find_set_metrics

logger.remove()
logger.add(sys.stderr, level="DEBUG")
app = FastAPI(version=__version__())

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthcheck", status_code=status.HTTP_200_OK)
def perform_healthcheck():
    return {"healthcheck": "OK"}


@app.get("/metrics", response_model=list[schemas.Dashboard])
def read_dashboard(
    response: Response, organization: str = "test"
) -> list[schemas.Dashboard]:

    logger.debug(f"Organization: {organization}")

    table = dynamodb.Table(ML_RESULTS_TABLE)

    query = table.query(
        IndexName="source-class-index",
        KeyConditionExpression=conditions.Key("source").eq(organization),
    )
    logger.trace(f"Query: {json.dumps(query, indent=2, cls=JSONEcoder)}")
    if query["Count"] == 0:
        raise HTTPException(status_code=404, detail="No dashboard found")
    dashboard = []
    assert isinstance(query, dict)
    for item in query["Items"]:
        item = json.loads(json.dumps(item, cls=JSONEcoder))
        index = item["source#host_id#service_id"]
        item["host_id"] = index.split("#")[1]
        item["service_id"] = index.split("#")[2]
        item["metric_name"] = item["class"]
        del item["source#host_id#service_id"]
        del item["class"]
        dashboard.append(item)
    logger.trace(f"Dashboard: {json.dumps(dashboard, indent=2)}")
    return dashboard


@app.get("/predictions/{uuid}", response_model=schemas.Prediction)
def read_predictions(uuid: str) -> schemas.Prediction:
    """
    Retrieve Forecasts from S3 bucket
    """
    try:
        s3_client = s3.meta.client
        obj = s3_client.get_object(Bucket=ML_RESULTS_BUCKET, Key=f"{uuid}.json")[
            "Body"
        ].read()
        logger.trace(f"Predictions: {json.dumps(json.loads(obj), indent=2)}")
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            raise HTTPException(status_code=404, detail="No prediction found")
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to get predictions with error {e}"
            )
    return json.loads(obj)


@app.post("/forecast")
def forecast(
    background_tasks: BackgroundTasks,
    organization: str = "test",
    forecasting_horizon: int = HORIZON_PREDICTION_HOURS,
) -> Response:
    """
    Make forecasts for all metrics in the database.

    Models are trained on all the historical data available for each metric and
    forecasts are stored in the S3 bucket and metadata are stored in Dynamodb.

    Note that models are calculated in a background task, so the response is
    returned immediately.
    """

    try:
        unique_labels = find_set_metrics(token=WARP10_READ_TOKEN)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get Warp10 data with error {e}"
        )

    if len(unique_labels) == 0:
        raise HTTPException(status_code=404, detail="No metrics found")

    background_tasks.add_task(
        make_forecasts,
        unique_labels=unique_labels,
        read_token=WARP10_READ_TOKEN,
        organization=organization,
        forecasting_horizon=forecasting_horizon,
    )

    return Response(status_code=202)
