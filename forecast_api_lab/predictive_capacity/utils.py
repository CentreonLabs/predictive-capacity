import datetime
import decimal
import json
from uuid import uuid4

from loguru import logger

from predictive_capacity import ML_RESULTS_TABLE, dynamodb


class JSONEcoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            if obj % 1 > 0:
                return float(obj)
            else:
                return int(obj)
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super(JSONEcoder, self).default(obj)


def get_uuid(
    source: str,
    metric_name: str,
    host_id: str,
    service_id: str,
    table_name: str = ML_RESULTS_TABLE,
):
    """Retrieve or create a UUID for a metric.

    Fetch the uuid of a metric from dynamodb. If the metric does not exist, create a new
    uuid and add it to the database.

    Parameters
    ----------
    source: str
    metric_name: str
    host_id: str
    service_id: str
    table_name: str

    Returns
    -------
    uuid: str
    """

    table = dynamodb.Table(table_name)
    response = table.get_item(
        Key={
            "class": metric_name,
            "source#host_id#service_id": f"{source}#{host_id}#{service_id}",
        }
    )
    if "Item" in response:
        uuid = str(response["Item"]["uuid"])
        logger.info(f"Metadata for {metric_name} already exists: {uuid}.")
    else:
        uuid = str(uuid4())
        logger.info(
            f"Metadata for {metric_name} does not exist. Creating a new one: {uuid}."
        )
    return uuid
