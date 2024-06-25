from typing import Literal

import pandas as pd
from loguru import logger
from pywarp10 import Warpscript

from predictive_capacity import ML_WARP10_URL, WARP10_SSL_VERIFY


def get_metric_saturation(
    token: str,
    name: str,
    labels: dict[str, str],
    saturation: Literal["min", "max"] = "max",
) -> float:
    """
    Function that gets the maximum allowed value for the metric

    Parameters
    ----------
    token: str
        Token to read the metrics from Warp10.

    name: str
        Name of the metric

    labels: dict[str, str]
        Labels of the metric. Must contains at least `host_id` and `service_id`.

    saturation: Literal["min", "max"]
        Whether to get the minimum or maximum allowed value

    Returns
    -------
    float
        Minimum or maximum allowed value for the metric

    """
    wp = Warpscript(host=ML_WARP10_URL, connection="http", verify=WARP10_SSL_VERIFY)
    name_saturation = f"{name}:{saturation}"
    wp.script(
        {
            "token": token,
            "class": name_saturation,
            "labels": labels,
            "end": "ws:NOW",
            "count": 1,
        },
        fun="FETCH",
    )
    logger.trace(wp.warpscript)
    values = wp.exec()
    assert isinstance(values, pd.DataFrame), "FETCH should return a DataFrame."
    if len(values) == 0:
        msg = f"No maximum value found for metric {name}{{{labels}}}."
        logger.error(msg)
        raise ValueError(msg)
    return values[name_saturation].values[0]
