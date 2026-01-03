import pytest
import os
from source import get_new_command, DEFAULT_SETTINGS

def test_column_info_ignored_with_custom_settings(monkeypatch):
    """Test that get_new_command honors fixcolcmd and column information.
    
    Bug: get_new_command ignores 'fixcolcmd' and the 'col' group when
    building the editor command, even if provided in settings and matched.
    """
    # Simulate a stack trace with file, line, and column
    stderr_with_column = "path/to/file.py:10:25: Error message"

    # Mock the EDITOR environment variable for consistent testing
    monkeypatch.setenv("EDITOR", "my_editor")

    # Define custom settings that include a fixcolcmd.
    # The bug is that 'get_new_command' ignores 'fixcolcmd' and column information.
    custom_settings = dict(DEFAULT_SETTINGS)
    custom_settings["fixcolcmd"] = "{editor} {file} +{line}:{col}"

    # Call the function under test with custom settings
    command = get_new_command(stderr_with_column, settings=custom_settings)

    # The buggy code will only use 'fixlinecmd' and ignore 'fixcolcmd' and the 'col' group.
    # It will produce: "my_editor path/to/file.py +10"

    # A fixed version, however, should honor 'fixcolcmd' and include the column.
    # It would produce: "my_editor path/to/file.py +10:25"
    expected_fixed_command = "my_editor path/to/file.py +10:25"

    # This assertion will FAIL on the buggy code because the actual command
    # (my_editor path/to/file.py +10) does not match the expected fixed command.
    assert command == expected_fixed_command, (
        f"Expected command to use fixcolcmd and include column info, "
        f"'{expected_fixed_command}', but got '{command}'. "
        f"The bug causes column info to be ignored."
    )
