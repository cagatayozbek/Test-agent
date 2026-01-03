import pytest
from source import get_user_display_name

def test_missing_profile_key_returns_anonymous():
    """
    Tests that get_user_display_name handles a user_data dictionary missing the 'profile' key.

    Bug: The code does not check if `user_data.get('profile')` returns None
    before attempting to access a key on it, which raises a TypeError.
    The fixed code is expected to handle this case gracefully and return 'Anonymous'.
    """
    # This user data dictionary is missing the 'profile' key.
    # This will cause `profile` to become None in the buggy function.
    user_data_without_profile = {'id': 1, 'username': 'user_no_profile'}

    # In the buggy code, this call will raise a TypeError: 'NoneType' object is not subscriptable
    # In the fixed code, this should return the default safe value 'Anonymous'.
    result = get_user_display_name(user_data_without_profile)

    assert result == 'Anonymous', (
        f"Expected 'Anonymous' when 'profile' key is missing, but got: {result}"
    )
