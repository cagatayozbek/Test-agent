import pytest
from source import get_user_display_name

def test_get_user_display_name_with_missing_profile():
    """Test that get_user_display_name handles missing 'profile' key gracefully.
    
    Bug: Attempts to access 'display_name' on a None object when 'profile' is missing
    from user_data, leading to a TypeError. This test expects the fixed code
    to return None in such a scenario.
    """
    # User data where the 'profile' key is completely missing
    user_data_missing_profile = {
        'user_id': 'user123',
        'username': 'testuser'
    }

    # User data where the 'profile' key exists but its value is None
    user_data_null_profile = {
        'user_id': 'user456',
        'profile': None
    }

    # --- Test case 1: 'profile' key is missing ---
    # Buggy code: get('profile') returns None, then None['display_name'] raises TypeError.
    # Fixed code (expected): Should handle None gracefully and return None.
    result_missing = get_user_display_name(user_data_missing_profile)
    assert result_missing is None, (
        "Expected None when 'profile' key is missing from user_data, "
        f"but got '{result_missing}'. Buggy code would raise TypeError here."
    )

    # --- Test case 2: 'profile' key is present but its value is None ---
    # Buggy code: get('profile') returns None, then None['display_name'] raises TypeError.
    # Fixed code (expected): Should handle None gracefully and return None.
    result_null = get_user_display_name(user_data_null_profile)
    assert result_null is None, (
        "Expected None when 'profile' key's value is None, "
        f"but got '{result_null}'. Buggy code would raise TypeError here."
    )