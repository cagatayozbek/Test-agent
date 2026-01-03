def get_user_display_name(user_data):
    """
    Returns the display name from user data.
    Expected structure: {'profile': {'display_name': '...', ...}, ...}
    However, the 'profile' key can sometimes be None.
    """
    # BUG: If user_data.get('profile') returns None,
    # accessing ['display_name'] on None raises TypeError.
    profile = user_data.get('profile')
    
    # The developer assumed profile is always present or forgot to check for None.
    return profile['display_name']
