import pytest
from source import UserSession

def test_cache_is_cleared_on_logout():
    """Tests that user data cache is cleared after logout.

    Bug: logout() method does not clear the internal cache, causing
    get_user_data() to return stale data instead of None for a
    logged-out session.
    """
    # 1. Create a session and log in to populate the cache
    session = UserSession()
    session.login(user_id="user123")

    # Sanity check: ensure data is present after login
    assert session.get_user_data() is not None, "Data should exist after login"

    # 2. Log out - this is where the cache should be cleared
    session.logout()

    # 3. Attempt to get user data again
    post_logout_data = session.get_user_data()

    # 4. Assert that the data is now None, as expected for a logged-out user
    # This assertion will FAIL on the buggy code because the cache was not cleared.
    assert post_logout_data is None, (
        f"get_user_data() should return None after logout, but it returned "
        f"stale cached data: {post_logout_data}"
    )