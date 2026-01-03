import asyncio

class AsyncCounter:
    def __init__(self):
        self.count = 0

    async def increment(self):
        # BUG: Read and write are not atomic and there is no lock.
        # During the await (context switch), another task can read the same self.count.
        temp = self.count
        await asyncio.sleep(0.01)  # Simulate DB or I/O latency
        self.count = temp + 1

async def run_race():
    counter = AsyncCounter()
    # Start 50 concurrent increment operations
    await asyncio.gather(*[counter.increment() for _ in range(50)])
    return counter.count
