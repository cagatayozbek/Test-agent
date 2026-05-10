import os
import sys

test_dir = os.path.dirname(os.path.abspath(__file__))
buggy_dir = os.path.join(os.path.dirname(test_dir), 'buggy')
sys.path.insert(0, buggy_dir)
import source


def test_source_importable():
    assert source is not None


def test_map_obj_to_commands_preserves_leading_trailing_spaces_in_banner_text():
    """
    Bug: map_obj_to_commands calls want['text'].strip() which strips ALL whitespace
    including leading/trailing spaces that may be meaningful in banner text.
    Fixed: uses want['text'].strip('\\n') which only strips newlines, preserving spaces.

    This test FAILS on buggy code (spaces are stripped away) and
    PASSES on fixed code (spaces are preserved).
    """
    class FakeModule:
        params = {'banner': 'login', 'state': 'present'}

    # Banner text with leading and trailing spaces (meaningful whitespace)
    banner_text = "  indented banner line  "
    want = {'text': banner_text, 'state': 'present'}
    have = {}

    commands = source.map_obj_to_commands((want, have), FakeModule())

    assert len(commands) == 1
    cmd = commands[0]
    # Fixed (strip('\n')): spaces are preserved → "  indented banner line  " in cmd
    # Buggy (strip()):      spaces are removed  → "indented banner line" in cmd
    assert '  indented banner line  ' in cmd, (
        "Bug detected: leading/trailing spaces in banner text were stripped. "
        "Got command: %r" % cmd
    )


def test_map_params_to_obj_preserves_whitespace_in_text():
    """
    Bug: map_params_to_obj calls str(text).strip() which strips ALL whitespace
    from the text parameter, destroying meaningful leading/trailing spaces.
    Fixed: the strip() call is removed entirely.

    This test FAILS on buggy code (spaces stripped by map_params_to_obj) and
    PASSES on fixed code (text returned unchanged).
    """
    class FakeModule:
        params = {
            'banner': 'login',
            'text': '  indented banner  ',
            'state': 'present',
        }

    result = source.map_params_to_obj(FakeModule())

    # Buggy:  str(text).strip() → 'indented banner'   (spaces gone)
    # Fixed:  no strip          → '  indented banner  ' (spaces kept)
    assert result['text'] == '  indented banner  ', (
        "Bug detected: map_params_to_obj stripped whitespace from banner text. "
        "Got: %r" % result['text']
    )


def test_map_obj_to_commands_multiline_preserves_leading_spaces():
    """
    Buggy: want['text'].strip() strips ALL whitespace — including leading spaces
    on the first line of a multiline banner.
    Fixed: want['text'].strip('\\n') strips only newlines, preserving spaces.

    Input text starts with spaces followed by a newline + second line.
    strip()    → removes the leading spaces → '   line1' becomes 'line1'
    strip('\\n') → only strips leading/trailing newlines → '   line1' is preserved.

    FAILS on buggy (leading spaces stripped), PASSES on fixed (spaces kept).
    """
    class FakeModule:
        params = {'banner': 'login', 'state': 'present'}

    # Leading spaces on first line are meaningful (indentation / formatting)
    banner_text = '   indented first line\nsecond line'
    want = {'text': banner_text, 'state': 'present'}
    have = {}

    commands = source.map_obj_to_commands((want, have), FakeModule())

    assert len(commands) == 1, "Expected exactly one command"
    cmd = commands[0]
    # Buggy strip():   '   indented first line\nsecond line' → 'indented first line\nsecond line'
    # Fixed strip('\n'): unchanged because no leading/trailing newlines
    assert '   indented first line' in cmd, (
        "Bug detected: strip() removed meaningful leading spaces from banner text. "
        "Got command: %r" % cmd
    )


def test_map_obj_to_commands_preserves_leading_tab_in_banner_text():
    """
    Buggy:  want['text'].strip()    → removes ALL whitespace (spaces, tabs, newlines)
    Fixed:  want['text'].strip('\\n') → removes ONLY newlines, preserving tabs/spaces.

    Banner text that starts with a tab \\t has a meaningful leading character that
    strip() silently destroys.  strip('\\n') leaves it intact.

    FAILS on buggy (leading tab stripped), PASSES on fixed (leading tab preserved).
    """
    class FakeModule:
        params = {'banner': 'login', 'state': 'present'}

    # Tab-indented banner — common when banner is pasted from an editor or script
    banner_text = "\tWelcome to the device\n\tUnauthorized access is prohibited"
    want = {'text': banner_text, 'state': 'present'}
    have = {}

    commands = source.map_obj_to_commands((want, have), FakeModule())

    assert len(commands) == 1, "Expected exactly one banner command"
    cmd = commands[0]

    # Buggy strip():    "\tWelcome..." → "Welcome..." (leading tab removed)
    # Fixed strip('\n'): "\tWelcome..." → "\tWelcome..." (leading tab kept)
    assert '\tWelcome to the device' in cmd, (
        "Bug detected: strip() removed the leading tab character from banner text. "
        "Got command: %r" % cmd
    )


def test_strip_in_map_params_to_obj_causes_false_noop_when_want_matches_have():
    """
    When map_params_to_obj strips whitespace from the user-supplied text, the
    resulting want['text'] can accidentally equal have['text'] even though the
    user intends a different (whitespace-padded) banner.  That makes
    map_obj_to_commands skip command generation — a silent no-op.

    Buggy:  map_params_to_obj strips '  banner message  ' -> 'banner message'
            == have['text'] -> NO command generated (wrong)
    Fixed:  map_params_to_obj keeps '  banner message  '
            != have['text'] -> command IS generated (correct)

    FAILS on buggy code (no commands produced), PASSES on fixed code (1 command).
    """
    class FakeParamsModule:
        params = {
            'banner': 'login',
            'text': '  banner message  ',   # user wants text WITH surrounding spaces
            'state': 'present',
        }

    class FakeCommandsModule:
        params = {'banner': 'login', 'state': 'present'}

    # Device currently has the bare text WITHOUT surrounding spaces
    have = {'text': 'banner message', 'state': 'present'}

    want = source.map_params_to_obj(FakeParamsModule())
    # Buggy:  want['text'] == 'banner message'       (stripped, now equals have)
    # Fixed:  want['text'] == '  banner message  '   (preserved, differs from have)

    commands = source.map_obj_to_commands((want, have), FakeCommandsModule())

    assert len(commands) == 1, (
        "Bug: map_params_to_obj stripped whitespace, making want == have so no "
        "update command was generated. want['text']=%r, have['text']=%r, commands=%r"
        % (want['text'], have['text'], commands)
    )


def test_map_obj_to_commands_newline_prefixed_text_preserves_indentation():
    """
    Text that starts with a newline (common in YAML block scalars) followed by
    indented content.  strip() removes the leading \\n AND the spaces that follow
    it; strip('\\n') removes only the \\n, leaving the indentation intact.

    Buggy: '\\n  Welcome\\n'.strip()     == 'Welcome'    (indentation destroyed)
    Fixed: '\\n  Welcome\\n'.strip('\\n') == '  Welcome'  (indentation preserved)

    FAILS on buggy code (spaces after leading newline stripped), PASSES on fixed.
    """
    class FakeModule:
        params = {'banner': 'login', 'state': 'present'}

    banner_text = '\n  Welcome to the router\n'
    want = {'text': banner_text, 'state': 'present'}
    have = {}

    commands = source.map_obj_to_commands((want, have), FakeModule())

    assert len(commands) == 1, "Expected exactly one banner command"
    cmd = commands[0]
    # Buggy strip():     '\n  Welcome to the router\n' -> 'Welcome to the router'
    # Fixed strip('\n'): '\n  Welcome to the router\n' -> '  Welcome to the router'
    assert '  Welcome to the router' in cmd, (
        "Bug detected: strip() removed indentation spaces after leading newline. "
        "Got command: %r" % cmd
    )


def test_map_obj_to_commands_preserves_trailing_spaces_before_newline():
    """
    Banner text ending with spaces then a newline (common in copy-pasted configs).
    strip()     removes the trailing newline AND the spaces that precede it.
    strip('\\n') removes only the newline, leaving the trailing spaces intact.

    Buggy:  'Welcome  \\n'.strip()     == 'Welcome'    (trailing spaces destroyed)
    Fixed:  'Welcome  \\n'.strip('\\n') == 'Welcome  '  (trailing spaces preserved)

    FAILS on buggy code (trailing spaces stripped), PASSES on fixed code.
    """
    class FakeModule:
        params = {'banner': 'login', 'state': 'present'}

    banner_text = 'Welcome to the device  \n'
    want = {'text': banner_text, 'state': 'present'}
    have = {}

    commands = source.map_obj_to_commands((want, have), FakeModule())

    assert len(commands) == 1, "Expected exactly one banner command"
    cmd = commands[0]
    # Buggy strip():    'Welcome to the device  \n' -> 'Welcome to the device'
    # Fixed strip('\n'): 'Welcome to the device  \n' -> 'Welcome to the device  '
    assert 'Welcome to the device  ' in cmd, (
        "Bug detected: strip() removed trailing spaces before trailing newline. "
        "Got command: %r" % cmd
    )
