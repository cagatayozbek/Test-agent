import pytest
from source import get_user_display_name

def test_get_display_name_with_null_profile_returns_none():
    """Test that get_user_display_name gracefully handles a None 'profile'.
    
    Bug: The original code raises a TypeError when 'profile' is None because it
    attempts to access a key on a None object. The fixed code should handle this
    case gracefully, typically by returning None or an empty string.
    """
    user_data_with_null_profile = {
        'user_id': 'test_user_id_123',
        'username': 'testuser',
        'profile': None  # This specifically triggers the bug condition
    }

    # On the buggy code, this call will raise a TypeError: "'NoneType' object is not subscriptable".
    # Since the test does not expect this TypeError (e.g., via pytest.raises), it will FAIL.
    # On the fixed code, assuming it handles None gracefully (e.g., returns None),
    # the test will capture None and the assertion will PASS.
    result = get_user_display_name(user_data_with_null_profile)

    assert result is None, (
        f"Expected get_user_display_name to return None when 'profile' is None "
        f"(for graceful handling), but got '{result}'. The buggy code would "
        f"instead raise a TypeError here." 
    )

