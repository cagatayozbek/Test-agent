import pytest
from source import fish_info


def test_fish_version_string_contains_prefix():
    """Test that fish_info returns the version string without the 'fish, version' prefix.
    \n    Bug: The fish_info function includes the full output of the fish command, including the prefix.\n    """
    version_string = fish_info()
    assert "fish, version" not in version_string, f"Version string should not contain the 'fish, version' prefix. Got: {version_string}"
