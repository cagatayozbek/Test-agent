import pytest
from source import process_transaction


def test_name_error_is_raised():
    """Test that NameError is raised when calculate_tax is missing.

    Bug: The bare except: block in process_transaction swallows the NameError.
    """
    with pytest.raises(NameError):
        process_transaction("item1:100")
