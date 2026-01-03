import pytest
from source import get_user_display_name


def test_missing_profile_key():
    """Test that a missing 'profile' key raises a TypeError.

    Bug: Code doesn't handle missing 'profile' key, causing a TypeError.
    """
    user_data = {}
    with pytest.raises(TypeError):
        get_user_display_name(user_data)


def test_none_profile_value():
    """Test that a None 'profile' value raises a TypeError.

    Bug: Code doesn't handle None 'profile' value, causing a TypeError.
    """
    user_data = {'profile': None}
    with pytest.raises(TypeError):
        get_user_display_name(user_data)