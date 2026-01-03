import pytest
from source import fish_info

def test_fish_info_extracts_only_version_token():
    """Test that fish_info correctly extracts only the numeric version token.

    Bug: The `fish_info` function includes the 'fish, version ' prefix from
    the `_default_runner` output instead of parsing just the numeric version.
    This test asserts the expected *parsed* version string.
    """
    # The _default_runner in source.py returns "fish, version 3.1.2\n"
    # The buggy code will take this output, strip newlines, and prepend "Fish Shell ".
    # Expected buggy output: "Fish Shell fish, version 3.1.2"

    # A fixed version of fish_info should parse "fish, version 3.1.2\n"
    # to extract only "3.1.2" and then prepend "Fish Shell ".
    # Expected fixed output: "Fish Shell 3.1.2"
    expected_version_string = "Fish Shell 3.1.2"

    actual_version_string = fish_info()

    assert actual_version_string == expected_version_string, (
        f"Expected fish_info to return '{expected_version_string}', "
        f"but got '{actual_version_string}'. The bug causes it to "
        f"include the 'fish, version ' prefix in the version string."
    )
