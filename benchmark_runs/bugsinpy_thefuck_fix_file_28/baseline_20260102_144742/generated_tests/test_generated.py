import pytest
import os
from source import get_new_command

def test_get_new_command_ignores_column_precision():
    """Test that get_new_command fails to build a column-precise editor command.

    Bug: get_new_command ignores column information and fixcolcmd, even when
    present in stderr and settings, resulting in a command lacking column precision.
    """
    # 1. Prepare stderr with file, line, and column information
    stderr_with_column = "src/main.py:25:10: TypeError: 'NoneType' object is not callable"

    # 2. Prepare custom settings including a 'fixcolcmd' which should be used
    custom_settings = {
        "fixlinecmd": "{editor} {file} +{line}",
        "fixcolcmd": "{editor} {file} +{line}:{col}",
    }

    # 3. Set a predictable EDITOR environment variable for test reliability
    original_editor = os.environ.get("EDITOR")
    os.environ["EDITOR"] = "code"

    try:
        # 4. Call the buggy function
        generated_command = get_new_command(stderr_with_column, settings=custom_settings)

        # 5. Define the command expected if the bug were fixed (i.e., column-aware)
        expected_command_fixed = "code src/main.py +25:10"

        # The buggy code will only use 'fixlinecmd', ignoring the 'col' group
        # and the 'fixcolcmd' setting. It will produce "code src/main.py +25".
        # Therefore, this assertion for the *fixed* behavior will FAIL on buggy code.
        assert generated_command == expected_command_fixed, (
            f"Bug detected: get_new_command ignored column precision. "
            f"Expected a column-aware command: '{expected_command_fixed}', "
            f"but got: '{generated_command}' (missing column)."
        )
    finally:
        # Cleanup os.environ to avoid affecting other tests or environment
        if original_editor is not None:
            os.environ["EDITOR"] = original_editor
        else:
            del os.environ["EDITOR"]
