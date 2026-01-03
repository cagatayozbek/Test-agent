import pytest
from source import get_user_display_name

def test_get_user_display_name_with_none_profile():
    """Test that get_user_display_name raises TypeError when 'profile' is None.
    
    Bug: Attempts to access ['display_name'] on a None object if 'profile' is None.
    """
    # User data where the 'profile' key is explicitly None
    user_data_with_none_profile = {
        'id': 1,
        'username': 'testuser',
        'profile': None
    }

    # The buggy code will attempt None['display_name'], which raises a TypeError
    with pytest.raises(TypeError) as excinfo:
        get_user_display_name(user_data_with_none_profile)

    assert "NoneType' object is not subscriptable" in str(excinfo.value)

def test_get_user_display_name_with_missing_profile():
    """Test that get_user_display_name raises TypeError when 'profile' key is missing.
    
    Bug: Attempts to access ['display_name'] on a None object if 'profile' is missing.
    """
    # User data where the 'profile' key is entirely missing
    user_data_missing_profile = {
        'id': 2,
        'username': 'anotheruser'
    }

    # The buggy code will call .get('profile') which returns None, then None['display_name']
    with pytest.raises(TypeError) as excinfo:
        get_user_display_name(user_data_missing_profile)

    assert "NoneType' object is not subscriptable" in str(excinfo.value)