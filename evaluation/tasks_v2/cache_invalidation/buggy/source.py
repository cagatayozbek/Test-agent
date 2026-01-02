"""User session manager with cache invalidation bug.

This module manages user sessions with caching for performance.
After logout, cached data should be cleared.

BUG: logout() doesn't clear the internal cache, causing stale
user data to be returned after logout.
"""

class UserSession:
    """Manages user login/logout with cached user data."""
    
    def __init__(self):
        self._logged_in = False
        self._user_id = None
        self._cache = {}  # User data cache
    
    def login(self, user_id: str) -> bool:
        """Log in a user and initialize their session."""
        self._logged_in = True
        self._user_id = user_id
        # Simulate fetching user data
        self._cache["user_data"] = {
            "id": user_id,
            "name": f"User_{user_id}",
            "preferences": {"theme": "dark"}
        }
        return True
    
    def logout(self) -> bool:
        """Log out the current user.
        
        BUG: Forgets to clear the cache!
        """
        self._logged_in = False
        self._user_id = None
        # BUG: Missing self._cache.clear() or self._cache = {}
        return True
    
    def is_logged_in(self) -> bool:
        """Check if a user is currently logged in."""
        return self._logged_in
    
    def get_user_data(self) -> dict | None:
        """Get cached user data.
        
        Returns:
            User data dict if logged in, None otherwise.
            
        BUG: Returns stale cached data even after logout!
        """
        if not self._logged_in:
            # BUG: Should return None, but cache still has data
            return self._cache.get("user_data")
        return self._cache.get("user_data")
    
    def get_current_user_id(self) -> str | None:
        """Get the current user's ID."""
        return self._user_id if self._logged_in else None
