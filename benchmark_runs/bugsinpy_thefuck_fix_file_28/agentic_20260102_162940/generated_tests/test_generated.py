import pytest
import os
from source import get_new_command

def test_uses_column_command_when_available():
    """Tests that get_new_command uses 'fixcolcmd' when a column is matched.

    Bug: The function always uses 'fixlinecmd', ignoring matched column
    information and the 'fixcolcmd' setting, leading to less precise
    editor commands.
    """
    # Arrange: This stderr format matches the pattern with a column group
    stderr_with_col = "src/main.py:42:5: Error: undefined variable"

    # Arrange: Provide settings with a specific command for column-aware fixes
    custom_settings = {
        "fixlinecmd": "{editor} {file} +{line}",
        "fixcolcmd": "{editor} {file} --line {line} --col {col}",
    }

    # Arrange: Set a predictable editor for the test
    os.environ['EDITOR'] = 'myedit'

    # Act: Generate the command
    command = get_new_command(stderr_with_col, settings=custom_settings)

    # Assert: The expected command should be built using 'fixcolcmd'
    expected_command = "myedit src/main.py --line 42 --col 5"

    assert command == expected_command, (
        f"Command should use 'fixcolcmd' for column-aware traces. "
        f"Expected: '{expected_command}', Got: '{command}'"
    )
