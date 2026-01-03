import pytest
from source import UserSession

def test_cache_is_cleared_on_logout():
    """
    Tests that user data cache is cleared after logout.

    Bug: The logout() method does not clear the internal _cache,
    causing get_user_data() to return stale data for a logged-out user.
    """
    # 1. Create a session and log in to populate the cache
    session = UserSession()
    session.login(user_id="user123")

    # Sanity check: ensure data is present after login
    data_before_logout = session.get_user_data()
    assert data_before_logout is not None, "Data should be available after login"
    assert data_before_logout["id"] == "user123"

    # 2. Log out - this is the buggy operation
    session.logout()

    # 3. Attempt to get user data again
    data_after_logout = session.get_user_data()

    # 4. Assert that no data is returned. This will fail on the buggy code.
    assert data_after_logout is None, (
        f"Expected user data to be None after logout, but received stale data: "
        f"{data_after_logout}"
    )
