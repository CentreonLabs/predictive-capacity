from typing import Any

import pandas as pd
import requests

from predictive_capacity import WARP10_SSL_VERIFY
from predictive_capacity.warp10.utils import build_gts_input_format, url_update


def upload_gts(
    token: str,
    name: str,
    labels: dict[str, str],
    timestamp: pd.Timestamp | int | str | list[pd.Timestamp] | list[int] | list[str],
    value: Any | list[Any],
):
    request = build_gts_input_format(
        value=value, timestamp=timestamp, labels=labels, name=name
    )

    headers = {"X-Warp10-Token": token}

    res = requests.post(
        url_update, headers=headers, data=request, verify=WARP10_SSL_VERIFY
    )
    if res.status_code != 200:
        raise requests.exceptions.HTTPError(
            f"Error while writing to Warp10: {res.status_code} - {res.text}"
        )
