import pytest
from source import get_user_display_name

def test_get_user_display_name_profile_is_none():
    """
    Test that get_user_display_name gracefully handles 'profile' being None,
    expecting it to return None instead of raising a TypeError.
    
    Bug: The code directly accesses ['display_name'] on 'profile' without
    checking if 'profile' itself is None, leading to a TypeError.
    """
    user_data = {"profile": None}
    
    # On the buggy code, calling get_user_display_name with {"profile": None}
    # will raise a TypeError before this assertion is reached, causing the test to FAIL.
    # A fixed version would handle this gracefully (e.g., return None), allowing the
    # assertion to pass.
    result = get_user_display_name(user_data)
    
    assert result is None, (
        f"Expected get_user_display_name to return None when 'profile' is None, "
        f"but it returned {result} instead. Check for TypeError if test failed before assertion."
    )