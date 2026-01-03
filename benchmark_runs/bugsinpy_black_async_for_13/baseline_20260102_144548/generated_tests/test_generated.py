import pytest
from source import tokenize_async, Token

def test_async_for_keyword_classification():
    """Test that 'async' followed by 'for' is correctly classified as an ASYNC token.

    Bug: The tokenizer stashes 'async' but only flushes it as an 'ASYNC' token
    when followed by 'def'. For 'async for' constructs, 'async' is emitted
    as a generic 'NAME' token or its 'ASYNC' classification is effectively 'dropped'.
    """
    input_tokens = ["async", "for", "item", "in", "items"]
    
    is_async_def, results = tokenize_async(input_tokens)
    
    # The buggy code will produce ('NAME', 'async') instead of ('ASYNC', 'async').
    # The test expects the correct classification.
    expected_async_token: Token = ("ASYNC", "async")
    
    assert expected_async_token in results, (
        f"Expected to find {expected_async_token} in the token list for 'async for' construct, "
        f"but it was not found. Instead, got {results}. The 'async' keyword was likely misclassified."
    )
    
    # For an 'async for' construct, the async_def flag should remain False.
    assert not is_async_def, (
        f"Expected is_async_def to be False for 'async for' construct, "
        f"but it was {is_async_def}."
    )

    # Further assertion to ensure the incorrect 'NAME' classification is not present
    # when the correct 'ASYNC' classification is expected.
    assert ("NAME", "async") not in results or expected_async_token in results, (
        f"Found an incorrectly classified ('NAME', 'async') token alongside or instead of "
        f"the expected {expected_async_token}. Results: {results}"
    )