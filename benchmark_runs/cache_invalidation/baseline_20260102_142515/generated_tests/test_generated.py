import pytest
from source import UserSession


def test_logout_clears_cache():
    """Test that logout() clears the cache, so get_user_data() returns None after logout.

    Bug: logout() doesn't clear the cache, causing stale data to persist.
    """
    session = UserSession()

    # Login a user
    session.login(user_id='testuser')
    assert session.is_logged_in(), "User should be logged in after login()"
    assert session.get_user_data() is not None, "User data should be available after login()"

    # Logout the user
    session.logout()
    assert not session.is_logged_in(), "User should be logged out after logout()"

    # Check if get_user_data() returns None after logout
    user_data_after_logout = session.get_user_data()
    assert user_data_after_logout is None, \
        f"User data should be None after logout, but got: {user_data_after_logout}"
