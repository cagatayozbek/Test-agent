import pytest
from source import get_user_display_name

def test_get_display_name_with_null_profile():
    """
    Tests that get_user_display_name handles cases where the 'profile' is None.

    Bug: The function attempts to access a key on the profile object without
    checking if the profile itself is None, leading to a TypeError.
    """
    # This input data mimics the scenario where the profile is explicitly None.
    user_data_with_null_profile = {'id': 1, 'profile': None}

    # In the buggy code, this call will raise a TypeError: 'NoneType' object is not subscriptable.
    # The fixed implementation handles this gracefully by returning the default display name.
    result = get_user_display_name(user_data_with_null_profile)

    assert result == "Anonymous", (
        f"Expected default display name for a user with a null profile, but got {result!r}"
    )
