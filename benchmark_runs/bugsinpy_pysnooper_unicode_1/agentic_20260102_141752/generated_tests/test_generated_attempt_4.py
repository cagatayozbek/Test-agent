import pytest
import os
from source import Tracer, detect_encoding

def test_unicode_output_corruption(tmpdir):
    """Test that non-ASCII output is correctly written to file with UTF-8 encoding.

    Bug: Tracer defaults to ASCII, leading to corruption of Unicode characters.
    """
    file_path = os.path.join(tmpdir, "test_output.txt")
    tracer = Tracer(file_path, overwrite=True)
    
    # Test case 1: With # coding: utf-8 declaration
    source_code_utf8 = [b'# coding: utf-8\n', b'print("你好，世界")']

    tracer.dump_source(source_code_utf8)

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "你好，世界" in content, f"UTF-8: Unicode characters were not correctly written. Got: {content}"

    # Test case 2: Without # coding: utf-8 declaration, assuming system default is not UTF-8
    tracer = Tracer(file_path, overwrite=True)
    source_code_no_encoding = [b'print("你好，世界")']
    tracer.dump_source(source_code_no_encoding)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    assert "你好，世界" in content, f"No encoding: Unicode characters were not correctly written. Got: {content}"