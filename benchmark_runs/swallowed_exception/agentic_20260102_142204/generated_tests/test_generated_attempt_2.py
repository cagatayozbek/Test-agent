import pytest
from source import process_transaction


def test_process_transaction_name_error():
    """Test that NameError is raised when calculate_tax is missing.

    Bug: process_transaction swallows NameError and returns None.
    """
    with pytest.raises(NameError) as excinfo:
        process_transaction("item1:100")
    assert "calculate_tax" in str(excinfo.value)
