import pytest
from source import get_user_display_name

def test_get_user_display_name_handles_null_profile():
    """Test that get_user_display_name gracefully handles missing or None profile data.
    
    Bug: The function attempts to access ['display_name'] on a None object when
    the 'profile' key is missing or explicitly None in user_data, raising TypeError.
    
    Fixed: The function should return a default value (e.g., 'Anonymous')
    instead of raising an error.
    """
    expected_display_name = 'Anonymous' # Based on feedback, fixed code returns 'Anonymous'

    # Test case 1: 'profile' key is explicitly None
    user_data_none_profile = {'id': 102, 'name': 'Another User', 'profile': None}
    
    # Buggy code will raise TypeError here. Fixed code should return 'Anonymous'.
    result_none_profile = get_user_display_name(user_data_none_profile)
    assert result_none_profile == expected_display_name, (
        f"When 'profile' is explicitly None, expected '{expected_display_name}', "
        f"but got '{result_none_profile}'"
    )

    # Test case 2: 'profile' key is entirely missing from user_data
    user_data_missing_profile = {'id': 101, 'name': 'Test User'}
    
    # Buggy code will raise TypeError here. Fixed code should return 'Anonymous'.
    result_missing_profile = get_user_display_name(user_data_missing_profile)
    assert result_missing_profile == expected_display_name, (
        f"When 'profile' key is missing, expected '{expected_display_name}', "
        f"but got '{result_missing_profile}'"
    )