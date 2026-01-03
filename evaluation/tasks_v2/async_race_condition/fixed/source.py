import asyncio

class AsyncCounter:
    def __init__(self):
        self.count = 0
        self._lock = asyncio.Lock() # FIX: Added lock mechanism.

    async def increment(self):
        async with self._lock: # FIX: Critical section is locked.
            temp = self.count
            await asyncio.sleep(0.01)
            self.count = temp + 1

async def run_race():
    counter = AsyncCounter()
    await asyncio.gather(*[counter.increment() for _ in range(50)])
    return counter.count
