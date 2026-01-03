import pytest
import asyncio

from source import AsyncCounter, run_race


@pytest.mark.asyncio
async def test_race_condition():
    """Test that the counter is incremented correctly with concurrent tasks.

    Bug: Concurrent increments are not atomic, leading to a lower final count.
    """
    num_trials = 10
    failures = 0
    for _ in range(num_trials):
        final_count = await run_race()
        if final_count != 50:
            failures += 1
    assert failures > 0, f"Expected failures in multiple trials due to race condition, but got {failures} failures out of {num_trials} trials."
