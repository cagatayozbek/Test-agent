import pytest
from source import run_race

@pytest.mark.asyncio
async def test_async_counter_race_condition():
    """
    Tests for the race condition in AsyncCounter.increment.

    The bug occurs because the read-modify-write operation is not atomic.
    The `await asyncio.sleep()` allows other tasks to read the old counter
    value before the current task can write the new one.

    This test runs 50 concurrent increments and asserts that the final count
    is 50. The buggy code will result in a much lower count,
    causing the assertion to fail.
    """
    # The run_race function from the source file runs 50 concurrent increments
    expected_count = 50

    # Execute the function that demonstrates the race condition
    final_count = await run_race()

    # On the buggy code, many increments will be lost, and final_count will be << 50
    assert final_count == expected_count, (
        f"Race condition detected in AsyncCounter. "
        f"Expected final count to be {expected_count}, but got {final_count}. "
        f"Increments were lost due to non-atomic operations."
    )