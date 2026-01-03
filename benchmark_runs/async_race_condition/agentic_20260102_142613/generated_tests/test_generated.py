import pytest
import asyncio
from source import AsyncCounter

@pytest.mark.asyncio
async def test_async_counter_race_condition():
    """Test for a race condition in AsyncCounter.increment method.
    
    Bug: Concurrent calls to increment lead to a final count less than the total
    number of increments due to non-atomic read-modify-write operations.
    The `await asyncio.sleep` allows other tasks to read stale data.
    """
    counter = AsyncCounter()
    num_concurrent_tasks = 50 # As used in the run_race example in source.py

    # Start multiple concurrent increment operations
    await asyncio.gather(*[counter.increment() for _ in range(num_concurrent_tasks)])

    # Due to the race condition, the final count will be less than the
    # total number of increments started.
    # The expected behavior for a correctly synchronized counter would be `num_concurrent_tasks`.
    assert counter.count == num_concurrent_tasks, (
        f"Race condition detected: Expected final count to be {num_concurrent_tasks}, "
        f"but got {counter.count}. This indicates lost increments due to concurrency."
    )
