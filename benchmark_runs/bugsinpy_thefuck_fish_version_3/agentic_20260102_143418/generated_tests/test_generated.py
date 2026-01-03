import pytest
from source import fish_info

def test_fish_info_extracts_version_token_only():
    """Test that fish_info extracts only the version number, not the full command output.
    
    Bug: The fish_info function incorrectly includes the full output from the shell
    command ('fish, version 3.1.2\n') instead of parsing it to get just '3.1.2'.
    """
    # When calling fish_info, the _default_runner provides 'fish, version 3.1.2\n'.
    # The buggy code will return 'Fish Shell fish, version 3.1.2'.
    # The fixed code should parse this to return 'Fish Shell 3.1.2'.
    
    expected_version = "3.1.2"
    result = fish_info()
    
    # The test should fail if 'fish, version' is present in the final string
    assert "fish, version" not in result, (
        f"Bug: 'fish, version' prefix found in '{result}'. "
        f"Expected only the version token after 'Fish Shell '."
    )
    
    # Ensure the actual version number is present and the overall format is correct
    assert result == f"Fish Shell {expected_version}", (
        f"Expected 'Fish Shell {expected_version}', but got '{result}'. "
        f"This indicates incorrect parsing or formatting."
    )