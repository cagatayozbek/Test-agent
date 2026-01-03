import pytest
from source import UserSession


def test_get_user_data_after_logout():
    """Test that get_user_data returns None after logout due to cache not clearing.\n    \n    Bug: logout() doesn't clear the internal cache, causing stale data to be returned.\n    """
    session = UserSession()
    
    # Login a user
    session.login(user_id='testuser')
    
    # Get user data while logged in
    user_data_before_logout = session.get_user_data()
    assert user_data_before_logout is not None
    
    # Logout the user
    session.logout()
    
    # Get user data after logout
    user_data_after_logout = session.get_user_data()
    
    # Assert that user data is None after logout
    assert user_data_after_logout is None, \
        "User data should be None after logout, but stale data was returned."
