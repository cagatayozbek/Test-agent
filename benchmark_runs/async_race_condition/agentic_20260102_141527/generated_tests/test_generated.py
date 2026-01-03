import pytest
import asyncio
from source import AsyncCounter, run_race

@pytest.mark.asyncio
async def test_race_condition():
    """Test that the AsyncCounter.increment method exhibits a race condition.

    The bug involves non-atomic updates to self.count, leading to lost increments
    when multiple tasks run concurrently.
    """
    final_count = await run_race()
    assert final_count < 50, f"Expected count to be less than 50 due to race condition, but got {final_count}"