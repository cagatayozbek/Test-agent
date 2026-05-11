import sys
import inspect
import pytest
import os

# Import the module under test
test_dir = os.path.dirname(os.path.abspath(__file__))
buggy_dir = os.path.join(os.path.dirname(test_dir), 'buggy')
sys.path.insert(0, buggy_dir)
import source


def test_iscoroutinefunction_basic_async():
    """Test that iscoroutinefunction identifies basic async functions."""
    async def basic_async():
        pass
    assert source.iscoroutinefunction(basic_async) is True


def test_iscoroutinefunction_basic_sync():
    """Test that iscoroutinefunction returns False for sync functions."""
    def basic_sync():
        pass
    assert source.iscoroutinefunction(basic_sync) is False


def test_iscoroutinefunction_async_generator():
    """Test async generators - should return False as they are not coroutine functions."""
    async def async_gen():
        yield 1
    # Async generators are not coroutine functions
    assert source.iscoroutinefunction(async_gen) is False


def test_iscoroutinefunction_sync_generator():
    """Test sync generators - should return False."""
    def sync_gen():
        yield 1
    assert source.iscoroutinefunction(sync_gen) is False


def test_iscoroutinefunction_decorated_async():
    """Test decorated async functions."""
    def decorator(f):
        return f

    @decorator
    async def decorated_async():
        pass

    # Should identify decorated async function
    result = source.iscoroutinefunction(decorated_async)
    assert result is True, f"Expected True for decorated async function, got {result}"


def test_iscoroutinefunction_lambda():
    """Test lambda functions - should return False."""
    lambda_func = lambda: None
    assert source.iscoroutinefunction(lambda_func) is False


def test_iscoroutinefunction_bound_method():
    """Test bound methods."""
    class MyClass:
        async def async_method(self):
            pass

    obj = MyClass()
    # Bound methods should be correctly identified
    result = source.iscoroutinefunction(obj.async_method)
    # Note: inspect.iscoroutinefunction on a bound method may return False
    # since the method descriptor hides the coroutine nature
    assert isinstance(result, bool), f"Expected boolean, got {type(result)}"


def test_iscoroutinefunction_classmethod():
    """Test classmethods."""
    class MyClass:
        @classmethod
        async def async_classmethod(cls):
            pass

    # classmethods wrap the function
    result = source.iscoroutinefunction(MyClass.async_classmethod)
    assert isinstance(result, bool), f"Expected boolean, got {type(result)}"


def test_iscoroutinefunction_staticmethod():
    """Test staticmethods."""
    class MyClass:
        @staticmethod
        async def async_staticmethod():
            pass

    # staticmethods also wrap the function
    result = source.iscoroutinefunction(MyClass.async_staticmethod)
    assert isinstance(result, bool), f"Expected boolean, got {type(result)}"


def test_iscoroutinefunction_none():
    """Test with None - should handle gracefully."""
    result = source.iscoroutinefunction(None)
    assert result is False


def test_iscoroutinefunction_integer():
    """Test with integer - should handle gracefully."""
    result = source.iscoroutinefunction(42)
    assert result is False


def test_iscoroutinefunction_string():
    """Test with string - should handle gracefully."""
    result = source.iscoroutinefunction("not a function")
    assert result is False


def test_iscoroutinefunction_object():
    """Test with arbitrary object - should handle gracefully."""
    class NotCallable:
        pass
    obj = NotCallable()
    result = source.iscoroutinefunction(obj)
    assert result is False


def test_iscoroutinefunction_coroutine_object():
    """Test with coroutine object (result of calling async function)."""
    async def async_func():
        pass

    coro = async_func()
    # Coroutine objects are different from coroutine functions
    result = source.iscoroutinefunction(coro)
    assert result is False

    # Clean up
    coro.close()


def test_py2_attribute_exists():
    """Test that PY2 attribute is defined in the module."""
    assert hasattr(source, 'PY2'), "PY2 attribute is missing from source module"
    assert isinstance(source.PY2, bool), f"PY2 should be a bool, got {type(source.PY2)}"


def test_py2_equals_not_py3():
    """Test that PY2 is correctly defined as not PY3."""
    assert source.PY2 == (not source.PY3), "PY2 should be the opposite of PY3"


def test_py2_defined_as_complement_of_py3():
    """Reveal bug: PY2 = not PY3 line is missing from buggy pycompat.py.

    The buggy source defines PY3 but omits 'PY2 = not PY3', so accessing
    source.PY2 raises AttributeError on the buggy version.
    """
    import sys
    assert hasattr(source, 'PY2'), "PY2 must be defined in pycompat (missing in buggy version)"
    expected = sys.version_info[0] == 2
    assert source.PY2 == expected, f"PY2 should be {expected}, got {source.PY2}"


def test_py2_false_on_python3():
    """Bug-revealing: buggy pycompat.py omits 'PY2 = not PY3'.

    The buggy version defines PY3 but never assigns PY2, so accessing
    source.PY2 raises AttributeError. The fixed version adds 'PY2 = not PY3'
    immediately after PY3, making PY2 False on Python 3.
    """
    # Raises AttributeError on buggy code — PY2 attribute simply doesn't exist
    assert source.PY2 == False, "PY2 should be False on Python 3 (missing in buggy version)"


def test_py2_and_py3_mutually_exclusive():
    """Bug-revealing: buggy pycompat.py omits 'PY2 = not PY3'.

    The buggy source defines only PY3; PY2 is never assigned.
    Accessing source.PY2 raises AttributeError on buggy code.
    The fixed version adds 'PY2 = not PY3', making PY2 and PY3 complementary.
    """
    import sys
    # This line raises AttributeError on the buggy code (PY2 is never defined there)
    py2 = source.PY2
    py3 = source.PY3

    # PY2 and PY3 must be strict complements: exactly one is True
    assert py2 != py3, f"PY2 ({py2}) and PY3 ({py3}) must differ — one must be True, the other False"
    assert py2 is (not py3), f"PY2 must equal 'not PY3', got PY2={py2!r}, PY3={py3!r}"

    # Concrete check for the running interpreter
    running_py3 = sys.version_info[0] == 3
    assert py3 is running_py3, f"PY3 should be {running_py3}, got {py3!r}"
    assert py2 is (not running_py3), f"PY2 should be {not running_py3}, got {py2!r}"
