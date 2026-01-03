import pytest
import os
from source import get_new_command

@pytest.fixture
def set_editor(monkeypatch):
    """Set the EDITOR environment variable for consistent test results."""
    monkeypatch.setenv("EDITOR", "vim")

def test_matches_pattern_with_unescaped_parentheses(set_editor):
    """Tests if the command is generated for stack traces with parentheses.
    
    Bug: A regex pattern for traces like 'file.py (line 10):' uses unescaped
    parentheses, causing it to fail to match. get_new_command returns None
    instead of a valid editor command.
    """
    # This stderr string is designed to be matched by the first pattern in PATTERNS.
    stderr_with_parens = "main.py (line 42): An error occurred"
    
    # Expected command if the buggy pattern were fixed.
    expected_command = "vim main.py +42"
    
    # On the buggy code, `_search` will fail to match and return None.
    actual_command = get_new_command(stderr_with_parens)
    
    # Assert that a command was generated, which will fail on the buggy code.
    assert actual_command is not None, "Expected a command, but got None due to regex match failure."
    assert actual_command == expected_command