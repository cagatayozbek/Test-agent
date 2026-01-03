def get_user_display_name(user_data):
    """
    Returns the display name from user data.
    Safely handles the case where 'profile' is None.
    """
    profile = user_data.get('profile')
    # FIX: Check if profile is not None before accessing its keys.
    if profile and 'display_name' in profile:
        return profile['display_name']
    return 'Anonymous'
