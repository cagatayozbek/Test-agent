import pytest
import asyncio
from source import AsyncCounter

@pytest.mark.asyncio
async def test_async_counter_race_condition():
    """Test that AsyncCounter's increment method handles concurrency correctly.
    
    Bug: Race condition causes concurrent increments to overwrite each other.
    The final count is less than the expected number of operations.
    """
    counter = AsyncCounter()
    num_increments = 50  # A sufficiently large number to reliably trigger the race condition

    # Create a list of coroutines to increment the counter concurrently
    increment_tasks = [counter.increment() for _ in range(num_increments)]

    # Run all increment operations concurrently
    await asyncio.gather(*increment_tasks)

    # On buggy code, the count will be less than num_increments
    # because `temp = self.count` and `self.count = temp + 1` are not atomic
    # and other tasks can read the stale `self.count` during the `await` pause.
    # On fixed code (e.g., using a lock), the count should be exactly num_increments.
    assert counter.count == num_increments, (
        f"Expected final count to be {num_increments} after {num_increments} concurrent increments, "
        f"but got {counter.count}. This indicates a race condition where increments were lost."
    )