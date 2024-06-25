from loguru import logger
from pywarp10 import Warpscript

from predictive_capacity import ML_WARP10_URL, WARP10_SSL_VERIFY


def get_label_name(
    token: str,
    name: str,
    labels: dict[str, str],
) -> tuple[str, str]:
    """
    Retrieve the name of the host or service

    Parameters
    ----------
    token: str
        Token to read the metrics from Warp10.
    name: str
        Name of the metric
    labels: dict[str, str]
        Labels of the metric. Must contains at least `host_id` and `service_id`.

    Returns
    -------
    Tuple[str, str]
        Name of the host and service.
    """
    host_name = labels["host_id"]
    service_name = labels["service_id"]
    wp = Warpscript(host=ML_WARP10_URL, connection="http", verify=WARP10_SSL_VERIFY)
    sets = wp.script([token, name, labels], fun="FINDSETS").exec()

    assert len(sets) == 3, "FINDSETS should return a set of 3 elements."
    if "host_name" in sets[1]:
        host_name = sets[1]["host_name"][0]
    if "service_name" in sets[1]:
        service_name = sets[1]["service_name"][0]

    logger.debug(f"host_name: {host_name}, service_name: {service_name}")

    return host_name, service_name
