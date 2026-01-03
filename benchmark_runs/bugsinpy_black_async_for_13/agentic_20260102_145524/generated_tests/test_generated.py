import pytest
from source import tokenize_async, Token
from typing import List

def test_async_for_is_tokenized_correctly():
    """Tests that 'async for' is tokenized correctly.

    The buggy code only recognizes 'async def' and misclassifies 'async'
    in an 'async for' loop as a NAME token instead of an ASYNC token.
    """
    # Input representing an 'async for' loop
    code_tokens = ['async', 'for', 'item', 'in', 'iterable']

    # The expected output where 'async' is correctly identified as a keyword
    expected_tokens: List[Token] = [
        ('ASYNC', 'async'),
        ('NAME', 'for'),
        ('NAME', 'item'),
        ('NAME', 'in'),
        ('NAME', 'iterable')
    ]

    # Run the tokenizer
    _async_def, actual_tokens = tokenize_async(code_tokens)

    # The buggy code will produce [('NAME', 'async'), ('NAME', 'for'), ...]
    assert actual_tokens == expected_tokens, (
        "Tokenizer failed to classify 'async' in 'async for' as ASYNC token. "
        f"Expected {expected_tokens}, but got {actual_tokens}"
    )