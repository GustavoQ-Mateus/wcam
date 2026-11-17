import asyncio
import contextlib

import psutil

SAMPLE_SECONDS = 1.0


class CpuMonitor:
    def __init__(self) -> None:
        self._process = psutil.Process()
        self._cpu_count = psutil.cpu_count() or 1
        self._children: dict[int, psutil.Process] = {}
        self.percent = 0.0

    async def run(self) -> None:
        self._process.cpu_percent(interval=None)
        while True:
            await asyncio.sleep(SAMPLE_SECONDS)
            total = self._process.cpu_percent(interval=None) + self._children_percent()
            self.percent = round(total / self._cpu_count, 1)

    def _children_percent(self) -> float:
        with contextlib.suppress(psutil.Error):
            current = {child.pid: child for child in self._process.children(recursive=True)}
            self._children = {pid: self._children.get(pid, child) for pid, child in current.items()}
        total = 0.0
        for child in self._children.values():
            with contextlib.suppress(psutil.Error):
                total += child.cpu_percent(interval=None)
        return total
