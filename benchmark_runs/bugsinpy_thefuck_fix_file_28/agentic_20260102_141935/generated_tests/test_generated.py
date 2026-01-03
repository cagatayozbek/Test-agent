import pytest
from source import get_new_command


def test_get_new_command_with_column_info():
    """Test that get_new_command uses fixcolcmd when column info is present.

    Bug: The function ignores column information and always uses fixlinecmd.
    """
    stderr = "file.py:10:5"
    settings = {
        "fixlinecmd": "{editor} {file} +{line}",
        "fixcolcmd": "{editor} {file} +{line} +{col}",
    }
    expected_command = "vim file.py +10 +5"
    
    result = get_new_command(stderr, settings)
    
    assert result == expected_command, f"Expected {expected_command}, but got {result}"


def test_get_new_command_with_column_info_no_fixcolcmd():
    """Test that get_new_command falls back to fixlinecmd when fixcolcmd is not provided.

    Bug: The function ignores column information and always uses fixlinecmd.
    """
    stderr = "file.py:10:5"
    settings = {
        "fixlinecmd": "{editor} {file} +{line}",
        "fixcolcmd": None,
    }
    expected_command = "vim file.py +10"

    result = get_new_command(stderr, settings)

    assert result == expected_command, f"Expected {expected_command}, but got {result}"