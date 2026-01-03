import pytest
from source import fish_info

def test_fish_info_parses_version_number():
    """Tests that fish_info extracts only the version number from command output.

    The buggy version includes the entire output string, like "fish, version 3.1.2",
    instead of parsing out just the version "3.1.2".
    """
    # The expected output after correct parsing
    expected_version_string = "Fish Shell 3.1.2"
    
    # Call the function, which uses the mocked runner
    actual_output = fish_info()
    
    # The buggy function will return "Fish Shell fish, version 3.1.2"
    # This assertion will fail on the buggy code and pass on the fixed code.
    assert actual_output == expected_version_string, (
        f"Expected only the version number to be appended. "
        f"Expected: '{expected_version_string}', Got: '{actual_output}'"
    )