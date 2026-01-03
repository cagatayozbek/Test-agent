import pytest
from source import fish_info

def test_fish_version_is_parsed():
    """Test that fish_info parses the version number from command output.

    The buggy code takes the entire output string from the command, resulting
    in a final string like "Fish Shell fish, version 3.1.2". The corrected
    code should parse the output to extract only the version token, like "3.1.2".
    """
    # The default runner in the source file simulates the output of the
    # fish command, returning "fish, version 3.1.2\n".

    # The function under test
    result = fish_info()

    # The expected output after correctly parsing the version number
    expected_output = "Fish Shell 3.1.2"

    # The buggy code will return "Fish Shell fish, version 3.1.2"
    assert result == expected_output, (
        f"Expected the version to be parsed correctly. \n"
        f"Expected: '{expected_output}', but got: '{result}'"
    )
