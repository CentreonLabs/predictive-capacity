from unittest.mock import MagicMock, patch

from moto import mock_dynamodb

from predictive_capacity.upload import create_dynamodb_table
from predictive_capacity.utils import get_uuid


@mock_dynamodb
@patch("predictive_capacity.utils.uuid4", return_value="1234")
def test_get_uuid(mock_uuid4: MagicMock):
    # The table needs to be created before we can use it
    table = create_dynamodb_table()
    assert get_uuid("source_test", "class_test", "host_test", "service_test") == "1234"
    mock_uuid4.assert_called_once()
    table.put_item(
        Item={
            "class": "class_test",
            "source#host_id#service_id": "source_test#host_test#service_test",
            "source": "source_test",
            "uuid": "1234",
        }
    )
    assert get_uuid("source_test", "class_test", "host_test", "service_test") == "1234"
    mock_uuid4.assert_called_once()
