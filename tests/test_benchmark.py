import sys
sys.path.insert(0, '/Users/cagatayozbek/Documents/Test-agent/evaluation/tasks_v2/quixbugs_bitcount/buggy')
from source import bitcount


def test_bitcount_multiple_bits():
    """
    Test bitcount with a number containing multiple 1-bits (127 = 0b1111111).

    The buggy version uses XOR (n ^= n - 1) instead of AND (n &= n - 1).
    XOR does not clear the lowest set bit, causing an infinite loop.
    This test will timeout/hang on the buggy code, revealing the bug.
    """
    assert bitcount(127) == 7
