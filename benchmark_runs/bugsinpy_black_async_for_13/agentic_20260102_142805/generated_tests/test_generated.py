import pytest
from source import tokenize_async

def test_async_for_keyword_classification():
    """Test that 'async' followed by 'for' is correctly classified as ASYNC.

    Bug: The 'async' token is misclassified as ('NAME', 'async') instead of
    ('ASYNC', 'async') when part of an 'async for' construct.
    """
    tokens = ["async", "for", "item"]
    
    # On a fixed version, 'async' in 'async for' should be ASYNC.
    # The async_def flag should be False as it's not 'async def'.
    expected_async_def_flag = False
    expected_result_tokens = [
        ("ASYNC", "async"),
        ("NAME", "for"),
        ("NAME", "item"),
    ]
    
    actual_async_def_flag, actual_result_tokens = tokenize_async(tokens)
    
    assert actual_async_def_flag == expected_async_def_flag, (
        f"Expected async_def flag to be {expected_async_def_flag}, "
        f"but got {actual_async_def_flag} for 'async for' construct."
    )
    assert actual_result_tokens == expected_result_tokens, (
        f"Tokenization mismatch for 'async for'.\n"
        f"Expected: {expected_result_tokens}\n"
        f"Got:      {actual_result_tokens}\n"
        f"The 'async' token should be classified as ('ASYNC', 'async')."
    )