import pytest
from source import UserSession

def test_get_user_data_after_logout_returns_none():
    """Tests that user data is not accessible after logout due to cache not being cleared.

    Bug: The logout() method fails to clear the internal `_cache`, causing
    get_user_data() to return stale data for a logged-out session.
    """
    # Arrange: Create a session and log in to populate the cache
    session = UserSession()
    user_id = "user_test_123"
    session.login(user_id)

    # Sanity check: ensure data is present before logout
    data_before_logout = session.get_user_data()
    assert data_before_logout is not None, "User data should exist after login"
    assert data_before_logout.get("id") == user_id

    # Act: Log the user out. This is where the bug lies.
    session.logout()

    # Act: Attempt to retrieve user data again after logout
    data_after_logout = session.get_user_data()

    # Assert: Check that the data is None, as the session is invalid.
    # This assertion will FAIL on the buggy code because the cache was not cleared.
    assert data_after_logout is None, (
        f"get_user_data() should return None after logout, but returned "
        f"stale cached data: {data_after_logout}"
    )