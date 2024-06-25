from loguru import logger
from pywarp10 import Warpscript

from predictive_capacity import ML_WARP10_URL, WARP10_SSL_VERIFY
from predictive_capacity.schemas import ResponseFindSetMetrics
from predictive_capacity.warp10.utils import path_warpscript


def find_set_metrics(token: str) -> list[ResponseFindSetMetrics]:
    """
    Find all the metrics for a given host/service/platform.

    Parameters
    ----------
    token: str
        Token to read the metrics from Warp10.

    Returns
    -------
    List[str]
        List of all the metrics/host/service/platform for a given organisation.
    """
    logger.debug(f"ML_WARP10_URL: {ML_WARP10_URL}")
    logger.debug(f"WARP10_SSL_VERIFY: {WARP10_SSL_VERIFY}")

    ws = Warpscript(host=ML_WARP10_URL, connection="http", verify=WARP10_SSL_VERIFY)
    ws.load(path_warpscript("find_set_metrics"), read_token=token)
    unique_labels = ws.exec(raw=True)[0]

    logger.debug(f"Found {len(unique_labels)} metrics in Warp10.")

    return [ResponseFindSetMetrics(**item) for item in unique_labels]
