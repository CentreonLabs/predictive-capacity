from unittest.mock import MagicMock, patch

from predictive_capacity.utils import get_uuid


@patch("predictive_capacity.utils.dynamodb")
@patch("predictive_capacity.utils.uuid4", return_value="1234")
def test_get_uuid(mock_uuid4: MagicMock, mock_dynamodb: MagicMock, dynamodb):
    # The table is automatically created in the conftest fixture.
    mock_dynamodb.return_value = dynamodb
    assert get_uuid("source_test", "class_test", "host_test", "service_test") == "1234"
    mock_uuid4.assert_called_once()
