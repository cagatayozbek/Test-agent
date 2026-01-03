import pytest
from source import fish_info


def test_fish_version_contains_prefix():
    """Test that fish_info returns only the version, without the 'fish, version' prefix.

    Bug: The fish_info function includes the full output string from the command,
    including the 'fish, version' prefix, instead of just the version number.
    """
    version_info = fish_info()
    assert "fish, version" not in version_info, \
        f"Fish info should not contain the 'fish, version' prefix, but got: {version_info}"
