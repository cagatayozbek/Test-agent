import pytest
from source import run_race, AsyncCounter

@pytest.mark.asyncio
async def test_async_counter_race_condition():
    """Test that the async counter is not susceptible to a race condition.

    Bug: The increment method reads the count, yields control during an await, and
    then writes the new value. Multiple concurrent tasks can read the same initial
    value, leading to lost increments.
    """
    # The run_race function from the source file runs 50 concurrent increments
    expected_count = 50
    
    # In the buggy version, many increments will be lost due to the race condition
    final_count = await run_race()
    
    assert final_count == expected_count, (
        f"Counter is subject to a race condition. "
        f"Expected final count to be {expected_count}, but got {final_count}."
    )
