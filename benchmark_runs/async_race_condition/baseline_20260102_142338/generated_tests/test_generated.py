import pytest
import asyncio
from source import AsyncCounter, run_race

@pytest.mark.asyncio
async def test_async_counter_race_condition():
    """Test that concurrent increments on AsyncCounter lead to race conditions without locking.
    
    Bug: Missing lock causes concurrent increments to overwrite each other.
    """
    final_count = await run_race()
    assert final_count == 50, f"Expected final count to be 50, but got {final_count}.  Race condition detected."
