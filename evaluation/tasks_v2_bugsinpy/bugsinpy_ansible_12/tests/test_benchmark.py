import os
import sys

test_dir = os.path.dirname(os.path.abspath(__file__))
buggy_dir = os.path.join(os.path.dirname(test_dir), 'buggy')


def test_source_exists():
    assert os.path.exists(os.path.join(buggy_dir, 'source.py'))


def test_lookup_env_uses_py3compat_not_os_getenv():
    """
    Bug: LookupModule.run uses os.getenv() instead of py3compat.environ.get().
    The buggy code imports 'os' and calls os.getenv(var, '') inside run(), bypassing
    Ansible's py3compat layer entirely.  The fixed code removes 'import os' and uses
    py3compat.environ.get(var, '') instead.

    FAILS on buggy code  (source text contains 'os.getenv').
    PASSES on fixed code (source text does not contain 'os.getenv').
    """
    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    assert 'os.getenv' not in source_text, (
        "Bug detected: source.py calls os.getenv() instead of py3compat.environ.get(). "
        "The env lookup plugin must use Ansible's py3compat layer for environment access."
    )


def test_run_method_calls_py3compat_environ_get():
    """
    AST-level check: the run() method must call py3compat.environ.get() to read
    environment variables. The buggy code instead calls os.getenv(), bypassing
    Ansible's py3compat portability layer.

    FAILS on buggy code  (no py3compat.environ.get call found in AST).
    PASSES on fixed code (py3compat.environ.get call present in AST).
    """
    import ast

    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    tree = ast.parse(source_text)

    py3compat_environ_get_calls = [
        node
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'get'
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == 'environ'
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == 'py3compat'
        )
    ]

    assert len(py3compat_environ_get_calls) > 0, (
        "Bug detected: source.py never calls py3compat.environ.get(). "
        "The env lookup plugin must use py3compat.environ.get(var, '') "
        "instead of os.getenv(var, '') so that environment access goes "
        "through Ansible's Python 2/3 compatibility layer."
    )


def test_run_method_actually_uses_py3compat_environ():
    """
    Runtime behavioral test: exec the module with a mock py3compat.environ
    and verify that run() calls py3compat.environ.get(), not os.getenv().

    FAILS on buggy code  (run uses os.getenv, never calls py3compat.environ.get).
    PASSES on fixed code (run calls py3compat.environ.get via mock).
    """
    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    calls = []

    class MockEnviron:
        def get(self, key, default=''):
            calls.append(key)
            return 'mocked_value'

    class MockPy3compat:
        environ = MockEnviron()

    # Patch the stub-based LookupBase with a real class so `class LookupModule(LookupBase)` works
    patched = source_text.replace('LookupBase = _Stub()', 'class LookupBase: pass', 1)

    # Namespace that prevents the in-source `py3compat = _Stub()` from overwriting our mock
    class ProtectedNamespace(dict):
        def __setitem__(self, key, value):
            if key == 'py3compat' and 'py3compat' in self:
                return
            super().__setitem__(key, value)

    namespace = ProtectedNamespace({'py3compat': MockPy3compat()})
    exec(patched, namespace)  # noqa: S102

    instance = namespace['LookupModule']()
    instance.run(['TEST_ANSIBLE_ENV_VAR'], {})

    assert len(calls) > 0, (
        "Bug detected: run() never called py3compat.environ.get(). "
        "The buggy code uses os.getenv() instead, bypassing Ansible's "
        "Python 2/3 compatibility layer."
    )
    assert calls[0] == 'TEST_ANSIBLE_ENV_VAR', (
        f"py3compat.environ.get was called with unexpected key: {calls}"
    )


def test_module_does_not_import_os():
    """
    Bug: buggy source contains 'import os' and calls os.getenv().
    The fixed version removes the 'import os' statement entirely, using
    py3compat.environ.get() instead.

    FAILS on buggy code  ('import os' is present in AST).
    PASSES on fixed code ('import os' is absent from AST).
    """
    import ast

    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    tree = ast.parse(source_text)

    os_imports = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        and any(alias.name == 'os' for alias in node.names)
    ]

    assert len(os_imports) == 0, (
        "Bug detected: source.py contains 'import os'. "
        "The fixed version removes this import entirely and uses "
        "py3compat.environ.get(var, '') instead of os.getenv(var, '')."
    )


def test_run_return_value_comes_from_py3compat_not_os():
    """
    Behavioral test: set a real env var, then intercept py3compat.environ.get
    to return a sentinel value. If run() uses py3compat, result is the sentinel;
    if it uses os.getenv, result is the real env value.

    FAILS on buggy code  (os.getenv returns the real env value, not 'INTERCEPTED').
    PASSES on fixed code (py3compat.environ.get returns 'INTERCEPTED').
    """
    import os

    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    test_key = 'ANSIBLE_BUGSINPY12_TEST_VAR'
    real_value = 'real_os_value_xyz'
    os.environ[test_key] = real_value

    try:
        class MockEnviron:
            def get(self, key, default=''):
                return 'INTERCEPTED'

        class MockPy3compat:
            environ = MockEnviron()

        # Replace the _Stub() instance with a proper base class so
        # `class LookupModule(LookupBase)` is valid in Python 3.
        patched = source_text.replace('LookupBase = _Stub()', 'class LookupBase: pass', 1)

        # ProtectedNamespace prevents any `py3compat = _Stub()` in the source
        # from overwriting our mock.
        class ProtectedNamespace(dict):
            def __setitem__(self, key, value):
                if key == 'py3compat' and 'py3compat' in self:
                    return
                super().__setitem__(key, value)

        namespace = ProtectedNamespace({'py3compat': MockPy3compat()})
        exec(patched, namespace)  # noqa: S102

        instance = namespace['LookupModule']()
        result = instance.run([test_key], {})

        assert result == ['INTERCEPTED'], (
            f"Bug detected: run() returned {result!r} (the real os env value) "
            f"instead of ['INTERCEPTED'] from the mocked py3compat.environ.get(). "
            f"The buggy code calls os.getenv() directly, bypassing Ansible's "
            f"py3compat portability layer."
        )
    finally:
        del os.environ[test_key]


def test_module_namespace_does_not_contain_os_module():
    """
    Runtime namespace check: exec the source and inspect what names end up
    in the module namespace. The buggy 'import os' statement puts the 'os'
    module object into the namespace; the fixed version removes that import
    entirely, so 'os' must be absent.

    FAILS on buggy code  ('import os' runs, so 'os' is in namespace).
    PASSES on fixed code (no 'import os', so 'os' is not in namespace).
    """
    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    patched = source_text.replace('LookupBase = _Stub()', 'class LookupBase: pass', 1)

    namespace = {}
    exec(patched, namespace)  # noqa: S102

    assert 'os' not in namespace, (
        "Bug detected: 'os' module is present in the module namespace after exec. "
        "The buggy source.py contains 'import os' (needed by os.getenv()), but the "
        "fixed version removes this import and uses py3compat.environ.get() instead."
    )


def test_run_multiple_terms_all_routed_through_py3compat():
    """
    Behavioral test: run() with multiple terms must route every lookup through
    py3compat.environ.get().  The buggy code calls os.getenv() directly, so our
    mock is never invoked and intercepted_keys stays empty.

    FAILS on buggy code  (os.getenv bypasses the mock; intercepted_keys == []).
    PASSES on fixed code (py3compat.environ.get called once per term).
    """
    source_path = os.path.join(buggy_dir, 'source.py')
    with open(source_path) as f:
        source_text = f.read()

    intercepted_keys = []

    class MockEnviron:
        def get(self, key, default=''):
            intercepted_keys.append(key)
            return f'intercepted_{key}'

    class MockPy3compat:
        environ = MockEnviron()

    # Replace the _Stub() instance so `class LookupModule(LookupBase)` is valid Python 3.
    patched = source_text.replace('LookupBase = _Stub()', 'class LookupBase: pass', 1)

    # Prevent `py3compat = _Stub()` inside the source from overwriting our mock.
    class ProtectedNamespace(dict):
        def __setitem__(self, key, value):
            if key == 'py3compat' and 'py3compat' in self:
                return
            super().__setitem__(key, value)

    namespace = ProtectedNamespace({'py3compat': MockPy3compat()})
    exec(patched, namespace)  # noqa: S102

    instance = namespace['LookupModule']()
    result = instance.run(['VAR_A', 'VAR_B', 'VAR_C'], {})

    assert intercepted_keys == ['VAR_A', 'VAR_B', 'VAR_C'], (
        f"Bug detected: py3compat.environ.get() was called for {intercepted_keys} "
        f"but expected ['VAR_A', 'VAR_B', 'VAR_C']. The buggy code uses os.getenv() "
        f"which bypasses our mock entirely, leaving intercepted_keys empty."
    )
    assert result == ['intercepted_VAR_A', 'intercepted_VAR_B', 'intercepted_VAR_C'], (
        f"Bug detected: run() returned {result!r} instead of py3compat-mocked values. "
        f"The buggy code reads from os.getenv() directly."
    )
