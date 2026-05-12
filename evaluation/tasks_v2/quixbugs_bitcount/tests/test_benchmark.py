import sys
sys.path.insert(0, '/Users/cagatayozbek/Documents/Test-agent/evaluation/tasks_v2/quixbugs_bitcount/buggy')

import source


def test_import():
    """Baseline test: ensure module imports."""
    assert source is not None


def test_bitcount_multiple_bits():
    """Test bitcount with input having multiple 1-bits (127 = 0b1111111)."""
    result = source.bitcount(127)
    assert result == 7


def test_bitcount_single_bit():
    """Test bitcount with input having a single 1-bit (128 = 0b10000000)."""
    result = source.bitcount(128)
    assert result == 1


def test_bitcount_zero():
    """Test bitcount with zero (no 1-bits)."""
    result = source.bitcount(0)
    assert result == 0
