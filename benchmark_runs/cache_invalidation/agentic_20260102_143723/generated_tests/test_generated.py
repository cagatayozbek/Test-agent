import pytest
from source import UserSession

def test_get_user_data_is_none_after_logout():
    """Test that get_user_data returns None after a user logs out due to cache not being cleared.
    
    Bug: logout() fails to clear _cache, causing get_user_data() to return stale data.
    """
    session = UserSession()
    user_id = "test_user_buggy"

    # 1. Log in a user to populate the cache
    assert session.login(user_id) is True, "Login should succeed"
    assert session.is_logged_in() is True, "User should be logged in after login"
    initial_user_data = session.get_user_data()
    assert initial_user_data is not None, "User data should be available immediately after login"
    assert initial_user_data["id"] == user_id, f"Expected user ID {user_id}, got {initial_user_data.get('id')}"

    # 2. Log out the user
    assert session.logout() is True, "Logout should succeed"
    assert session.is_logged_in() is False, "User should be logged out after logout"
    assert session.get_current_user_id() is None, "current_user_id should be None after logout"

    # 3. Critical assertion: Verify that after logout, get_user_data returns None.
    # The buggy code will return the stale 'initial_user_data' instead of None.
    post_logout_data = session.get_user_data()
    
    assert post_logout_data is None, (
        f"Expected get_user_data() to return None after logout due to cleared cache, "
        f"but got stale data: {post_logout_data}"
    )