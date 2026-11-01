import asyncio

import psutil

SAMPLE_SECONDS = 1.0


class CpuMonitor:
    def __init__(self) -> None:
        self._process = psutil.Process()
        self._cpu_count = psutil.cpu_count() or 1
        self.percent = 0.0

    async def run(self) -> None:
        self._process.cpu_percent(interval=None)
        while True:
            await asyncio.sleep(SAMPLE_SECONDS)
            self.percent = round(self._process.cpu_percent(interval=None) / self._cpu_count, 1)
