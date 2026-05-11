import sys
import os
import types
import importlib.util
import tempfile
import pytest

test_dir = os.path.dirname(os.path.abspath(__file__))
buggy_dir = os.path.join(os.path.dirname(test_dir), 'buggy')

# Set up a fake package so that "from . import utils, pycompat" in source.py works
_pkg_name = '_pysnooper_test_pkg'
if _pkg_name not in sys.modules:
    _pkg = types.ModuleType(_pkg_name)
    _pkg.__path__ = [buggy_dir]
    _pkg.__package__ = _pkg_name
    sys.modules[_pkg_name] = _pkg

    _utils = types.ModuleType(_pkg_name + '.utils')
    _utils.get_shortish_repr = lambda v, **kw: repr(v)
    _utils.file_reading_errors = (IOError, OSError)
    _utils.MAX_EXCEPTION_LENGTH = 200
    _utils.truncate = lambda s, n: s[:n] if len(s) > n else s
    _utils.ensure_tuple = lambda x: x if isinstance(x, tuple) else (x,) if x else ()
    _utils.WritableStream = type('WritableStream', (), {})
    _utils.shitcode = lambda s: s
    sys.modules[_pkg_name + '.utils'] = _utils
    sys.modules[_pkg_name].utils = _utils

    import collections.abc as _cabc
    _pycompat = types.ModuleType(_pkg_name + '.pycompat')
    _pycompat.PY2 = False
    _pycompat.text_type = str
    _pycompat.PathLike = os.PathLike
    _pycompat.iscoroutinefunction = None
    _pycompat.collections_abc = _cabc
    sys.modules[_pkg_name + '.pycompat'] = _pycompat
    sys.modules[_pkg_name].pycompat = _pycompat

_spec = importlib.util.spec_from_file_location(
    _pkg_name + '.tracer',
    os.path.join(buggy_dir, 'source.py'),
)
_source_mod = importlib.util.module_from_spec(_spec)
_source_mod.__package__ = _pkg_name
sys.modules[_pkg_name + '.tracer'] = _source_mod
_spec.loader.exec_module(_source_mod)

source = _source_mod


def test_source_is_not_none():
    assert source is not None


def test_utf8_source_encoding_default():
    """Bug: default encoding is 'ascii' instead of 'utf-8' in get_source_from_frame.

    When a UTF-8 source file has no coding declaration, get_source_from_frame
    defaults to 'ascii' (buggy) and decodes non-ASCII bytes as replacement chars.
    The fix changes the default to 'utf-8' so source lines are preserved correctly.

    This test FAILS on buggy code (ascii default mangles 'é à ü' to '???') and
    PASSES on fixed code (utf-8 default preserves them).
    """
    # UTF-8 encoded bytes with no coding declaration — the bug triggers here
    utf8_content = (
        b"# non-ASCII: \xc3\xa9 \xc3\xa0 \xc3\xbc\n"  # é à ü  (3 bytes each in UTF-8)
        b"def utf8_func():\n"
        b"    return 42\n"
    )

    with tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='wb') as f:
        f.write(utf8_content)
        tmp_path = f.name

    try:
        source.source_cache.clear()

        captured = []

        def capture_trace(frame, event, arg):
            if frame.f_code.co_filename == tmp_path and event == 'call':
                if not captured:
                    captured.append(frame)
            return capture_trace

        code = compile(utf8_content, tmp_path, 'exec')
        old_trace = sys.gettrace()
        sys.settrace(capture_trace)
        try:
            ns = {}
            exec(code, ns)          # defines utf8_func in ns
            ns['utf8_func']()       # call triggers the 'call' trace event
        finally:
            sys.settrace(old_trace)

        source.source_cache.clear()

        assert captured, "No frame captured from the temp module"
        frame = captured[0]

        lines = source.get_source_from_frame(frame)
        first_line = lines[0]

        # Buggy: 'ascii' default → é/à/ü become U+FFFD replacement chars ('�')
        # Fixed: 'utf-8' default → characters are preserved
        assert '�' not in first_line, (
            f"Non-ASCII bytes were corrupted (replacement chars found). "
            f"Got: {first_line!r}. "
            f"Bug: encoding defaults to 'ascii', should be 'utf-8'"
        )
        assert 'é' in first_line, (
            f"UTF-8 char 'é' not preserved in source line. Got: {first_line!r}. "
            f"Bug: encoding defaults to 'ascii', should be 'utf-8'"
        )
    finally:
        os.unlink(tmp_path)


def test_get_local_reprs_accepts_custom_repr():
    """Bug: get_local_reprs() is missing the custom_repr parameter.

    Buggy:  def get_local_reprs(frame, watch=())
    Fixed:  def get_local_reprs(frame, watch=(), custom_repr=())

    Calling with custom_repr= raises TypeError on buggy code, returns
    an OrderedDict on fixed code.  allow_bug_revealing=true
    """
    import inspect
    import collections

    frame = inspect.currentframe()
    # TypeError on buggy: unexpected keyword argument 'custom_repr'
    result = source.get_local_reprs(frame, custom_repr=())
    assert isinstance(result, collections.OrderedDict)


def test_file_writer_utf8_encoding():
    """Bug: FileWriter.write() does not pass encoding='utf-8' to open().

    The buggy code calls open() without specifying encoding, so on systems
    where the locale encoding is not UTF-8 (e.g. ASCII on many CI/Linux
    environments), writing non-ASCII trace output silently corrupts or raises
    UnicodeEncodeError.  The fix adds encoding='utf-8' to the open() call.

    This test simulates a non-UTF-8 locale by wrapping open() to force
    encoding='ascii' whenever no encoding is specified by the caller:
      - Buggy:  open() has no encoding kwarg → mock forces ASCII →
                writing non-ASCII chars raises UnicodeEncodeError (bug revealed)
      - Fixed:  open() passes encoding='utf-8' → mock leaves it alone →
                non-ASCII content is written successfully

    allow_bug_revealing=true
    """
    import unittest.mock as mock

    with tempfile.NamedTemporaryFile(suffix='.log', delete=False) as f:
        tmp_path = f.name

    try:
        fw = source.FileWriter(tmp_path, overwrite=True)

        real_open = open

        def ascii_locale_open(*args, **kwargs):
            if 'encoding' not in kwargs:
                kwargs['encoding'] = 'ascii'
            return real_open(*args, **kwargs)

        non_ascii_trace = 'Exception: café résumé naïve'

        with mock.patch('builtins.open', side_effect=ascii_locale_open):
            fw.write(non_ascii_trace)

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_disabled_flag_and_os_import():
    """Bug: 'import os' is missing, so DISABLED constant is not defined.

    The buggy tracer.py omits 'import os' and the corresponding module-level
    assignment:
        DISABLED = bool(os.getenv('PYSNOOPER_DISABLED', ''))

    Without 'import os', the DISABLED constant is never created.  On buggy
    code, accessing source.DISABLED raises AttributeError (caught here as a
    failing assertion).  On fixed code, source.DISABLED is a bool.

    This matches "Bug in import traceback" (bugsinpy PySnooper #2): the
    missing import causes the tracer to silently ignore the PYSNOOPER_DISABLED
    environment variable, and any attempt to read the flag fails entirely.

    allow_bug_revealing=true
    """
    assert hasattr(source, 'DISABLED'), (
        "DISABLED flag not found in source module: 'import os' and "
        "DISABLED = bool(os.getenv('PYSNOOPER_DISABLED', '')) are absent in "
        "the buggy version of tracer.py"
    )
    assert isinstance(source.DISABLED, bool), (
        f"source.DISABLED should be a bool, got {type(source.DISABLED)}"
    )


def test_tracer_accepts_custom_repr_kwarg():
    """Bug: Tracer.__init__() is missing the custom_repr parameter.

    Buggy tracer.py omits custom_repr from Tracer.__init__:
        def __init__(self, ..., thread_info=False)
    Fixed tracer.py adds it:
        def __init__(self, ..., thread_info=False, custom_repr=())

    On buggy code, Tracer(custom_repr=()) raises:
        TypeError: __init__() got an unexpected keyword argument 'custom_repr'
    On fixed code, it succeeds and self.custom_repr is set.

    allow_bug_revealing=true
    """
    import io

    output = io.StringIO()
    tracer = source.Tracer(output=output.write, custom_repr=())
    assert hasattr(tracer, 'custom_repr'), (
        "Tracer.custom_repr attribute missing — "
        "custom_repr parameter absent in buggy Tracer.__init__"
    )


def test_tracer_disabled_bypasses_wrapping():
    """Bug: Tracer.__call__ does not check DISABLED in the buggy version.

    Fixed tracer.py adds: if DISABLED: return function (early exit when disabled).
    Buggy tracer.py has no such check (and DISABLED is never even defined,
    because 'import os' is absent).

    With module-level DISABLED=True, the fixed Tracer.__call__ returns the
    original function unchanged. The buggy __call__ always wraps it regardless.

    allow_bug_revealing=true
    """
    import io

    old_iscoro = source.pycompat.iscoroutinefunction
    source.pycompat.iscoroutinefunction = lambda f: False

    old_disabled = getattr(source, 'DISABLED', None)
    try:
        source.DISABLED = True

        output = io.StringIO()
        tracer = source.Tracer(output=output.write)

        def original_func():
            return 42

        decorated = tracer(original_func)

        assert decorated is original_func, (
            "Tracer.__call__ should return the original function unchanged when "
            "DISABLED=True, but it wrapped the function instead. "
            "Bug: 'if DISABLED: return function' check is absent in buggy __call__."
        )
    finally:
        source.pycompat.iscoroutinefunction = old_iscoro
        if old_disabled is None:
            if hasattr(source, 'DISABLED'):
                del source.DISABLED
        else:
            source.DISABLED = old_disabled


def test_tracer_enter_disabled_skips_trace_setup():
    """Bug: Tracer.__enter__ does not check DISABLED in the buggy version.

    Fixed tracer.py adds an early return when DISABLED=True inside __enter__.
    Buggy tracer.py omits that check and always installs sys.settrace(self.trace).

    With DISABLED=True, the fixed __enter__ returns immediately without touching
    sys.settrace.  The buggy __enter__ installs the trace function regardless,
    so sys.gettrace() changes — which is what this test detects.

    allow_bug_revealing=true
    """
    import io

    had_disabled = hasattr(source, 'DISABLED')
    old_disabled = getattr(source, 'DISABLED', None)
    try:
        source.DISABLED = True

        output = io.StringIO()
        tracer = source.Tracer(output=output.write)

        original_trace = sys.gettrace()
        tracer.__enter__()
        trace_after_enter = sys.gettrace()
        # Always restore, even on buggy code that installed a trace
        tracer.__exit__(None, None, None)

        assert trace_after_enter is original_trace, (
            "Tracer.__enter__ changed sys.gettrace() despite DISABLED=True. "
            "Bug: 'if DISABLED: return' guard is absent in the buggy __enter__."
        )
    finally:
        if had_disabled:
            source.DISABLED = old_disabled
        elif hasattr(source, 'DISABLED'):
            del source.DISABLED
