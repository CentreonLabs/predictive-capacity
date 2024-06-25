from unittest.mock import patch

import pytest
import requests

from predictive_capacity import WARP10_SSL_VERIFY
from predictive_capacity.warp10.upload_gts import upload_gts


@patch(
    "predictive_capacity.warp10.upload_gts.build_gts_input_format",
)
@patch("predictive_capacity.warp10.upload_gts.requests.post")
@patch("predictive_capacity.warp10.upload_gts.url_update")
def test_upload_gts(mock_url_update, mock_post, mock_build_gts_input_format):
    mock_build_gts_input_format.return_value = "request"
    mock_post.return_value.status_code = 200
    upload_gts("token", "name", {"labels": "labels"}, "timestamp", "value")
    mock_build_gts_input_format.assert_called_once_with(
        value="value", timestamp="timestamp", labels={"labels": "labels"}, name="name"
    )
    mock_post.assert_called_once_with(
        mock_url_update,
        headers={"X-Warp10-Token": "token"},
        data="request",
        verify=WARP10_SSL_VERIFY,
    )
    mock_post.return_value.status_code = 400
    with pytest.raises(requests.exceptions.HTTPError):
        upload_gts("token", "name", {"labels": "labels"}, "timestamp", "value")
