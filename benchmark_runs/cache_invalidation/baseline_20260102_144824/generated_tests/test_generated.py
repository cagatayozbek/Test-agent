import pytest
from source import UserSession

def test_get_user_data_after_logout_is_none():
    """Test that get_user_data returns None after a user logs out.
    
    Bug: logout() fails to clear the internal cache, causing get_user_data()
    to return stale cached data instead of None post-logout.
    """
    session = UserSession()
    user_id = "test_user_123"

    # 1. Log in a user to populate the cache
    session.login(user_id=user_id)
    initial_data = session.get_user_data()
    assert initial_data is not None, "Pre-condition: User data should be available after login."
    assert initial_data.get("id") == user_id, "Pre-condition: Initial user data ID mismatch."
    
    # 2. Log out the user
    session.logout()
    
    # 3. Verify user is no longer logged in
    assert not session.is_logged_in(), "Expected user to be logged out."
    assert session.get_current_user_id() is None, "Expected current user ID to be None after logout."

    # 4. Attempt to retrieve user data after logout
    # This should return None if the cache was properly cleared
    post_logout_data = session.get_user_data()
    
    # CRITICAL ASSERTION: The bug causes this to return the stale cached data (a dict), not None.
    assert post_logout_data is None, (
        f"User data should be None after logout, but found stale data: {post_logout_data}. "
        f"The cache was not cleared by logout()."
    )