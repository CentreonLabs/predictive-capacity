import pandas as pd
from loguru import logger
from pywarp10 import Warpscript

from predictive_capacity import ML_WARP10_URL, WARP10_SSL_VERIFY


def fetch_metric(token: str, name: str, labels: dict[str, str]) -> pd.DataFrame:
    """
    Function that gets the gts from the Warp10 database.

    Returns
    -------
    pd.DataFrame
        gts for the metric

    """
    wp = Warpscript(host=ML_WARP10_URL, connection="http", verify=WARP10_SSL_VERIFY)
    wp.script(
        {
            "token": token,
            "class": name,
            "labels": labels,
            "start": 0,
            "end": "NOW",
        },
        fun="FETCH",
    )
    logger.trace(wp.warpscript)
    res = wp.exec()
    assert isinstance(res, pd.DataFrame), "MLFETCH should return a DataFrame."
    assert isinstance(res.index, pd.DatetimeIndex), "Index should be a DatetimeIndex"
    return res
