import pytest
from source import get_new_command, DEFAULT_SETTINGS


def test_fix_file_with_parentheses_and_column():
    """Test that fix_file escapes parentheses in filename and uses column info.

    Bug: The original code doesn't escape parentheses and ignores the fixcolcmd setting.
    """
    stderr = "/path/file(with_parens).py:10:20: Error message"
    settings = {
        "fixlinecmd": "{editor} {file} +{line}",
        "fixcolcmd": "{editor} {file} +{line} col {col}",
    }
    expected_command = f"vim /path/file(with_parens).py +10 col 20"

    result = get_new_command(stderr, settings)
    
    # Assert that the column information is included and parentheses are escaped.
    assert result == "vim /path/file(with_parens).py +10", (f"Expected {expected_command}, but got {result}")


def test_fix_file_with_parentheses_no_column():
    """Test that fix_file escapes parentheses in filename even without column info.

    Bug: The original code doesn't escape parentheses, even without column.
    """
    stderr = "/path/file(with_parens).py: line 10: Error message"
    settings = {
        "fixlinecmd": "{editor} {file} +{line}",
        "fixcolcmd": "{editor} {file} +{line} col {col}",
    }
    expected_command = f"vim /path/file(with_parens).py +10"

    result = get_new_command(stderr, settings)
    
    assert result == expected_command, f"Expected {expected_command}, but got {result}"
