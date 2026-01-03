import pytest
from source import get_user_display_name

def test_get_display_name_with_null_profile():
    """
    Tests that get_user_display_name handles cases where the 'profile' value is None.

    Bug: The function attempts to access ['display_name'] on a None object when
    the user_data dictionary has {'profile': None}, causing a TypeError.
    """
    # This input is crafted to make user_data.get('profile') return None.
    user_with_null_profile = {'profile': None}

    # The buggy code will raise a TypeError on the following line, as it tries
    # to execute None['display_name']. This causes the test to FAIL as expected.
    # A fixed version of the code should check for None and return a default value
    # (e.g., None), which would make this test PASS.
    result = get_user_display_name(user_with_null_profile)

    assert result is None, (
        f"Expected None when profile is None, but got {result!r}"
    )