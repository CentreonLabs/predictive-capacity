import json
import os
import urllib.parse
from typing import Any, Union

import pandas as pd

from predictive_capacity import ML_WARP10_URL

url_update = ML_WARP10_URL + "/api/v0/update"


def path_warpscript(filename: str) -> str:
    """Return the path to a warpscript.

    Args:
        filename (str): Warpscript filename without the extension.

    Returns:
        str: Warpscript path.
    """
    return os.path.join(
        os.path.dirname(__file__), "warpscripts", ".".join([filename, "mc2"])
    )


def build_gts_input_format(
    name: str,
    labels: dict,
    value: Any | list[Any],
    timestamp: int | str | pd.Timestamp | list[int] | list[str] | list[pd.Timestamp],
) -> str:
    """Build the input format for a GTS.

    Args:
        name (str): GTS name.
        labels (dict): GTS labels.
        value (Any): GTS value. If not a number, string or boolean, it will be
            converted to a dict and then a json encoded string.
        timestamp (Union[int, pd.Timestamp]): GTS timestamp.

    Returns:
        str: GTS input format.
    """
    if not isinstance(timestamp, list):
        ltimestamp = [timestamp]
        value = [value]
    else:
        ltimestamp = timestamp

    if len(ltimestamp) == 0:
        raise ValueError("Timestamp cannot be empty.")

    if len(ltimestamp) != len(value):
        raise ValueError("Timestamp and value must have the same length.")

    timestamps_int: list[int] = []
    for i in range(len(ltimestamp)):
        t = ltimestamp[i]
        v = value[i]

        if isinstance(t, pd.Timestamp):
            now_μs = t.timestamp() * 1000000
            timestamps_int.append(int(now_μs))
        elif isinstance(t, str):
            timestamps_int.append(int(pd.Timestamp(t).timestamp() * 1000000))
        elif isinstance(t, int):
            timestamps_int.append(t)
        else:
            raise ValueError("Timestamp must be a string, int or pd.Timestamp.")

        if not isinstance(v, (int, float, str, bool)):
            value[i] = f"'{json.dumps(v)}'"

    labels_str = ""
    for k, v in labels.items():
        labels_str += f"{k}={urllib.parse.quote(v)},"

    request = f"{timestamps_int[0]}// {name}{{{labels_str[:-1]}}} {value[0]}\n"
    for i in range(1, len(ltimestamp)):
        request += f"={timestamps_int[i]}// {value[i]}\n"

    return request
