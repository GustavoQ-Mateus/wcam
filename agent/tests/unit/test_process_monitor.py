import asyncio
import contextlib
import sys

import psutil

from wcam.process_monitor import SAMPLE_SECONDS, CpuMonitor

SAMPLES = 3
BUSY_CHILD = "while True: pass"
SHARE_OF_A_BUSY_CORE = 0.5


async def test_cpu_includes_the_child_processes() -> None:
    monitor = CpuMonitor()
    child = await asyncio.create_subprocess_exec(sys.executable, "-c", BUSY_CHILD)
    sampling = asyncio.create_task(monitor.run())
    try:
        await asyncio.sleep(SAMPLE_SECONDS * SAMPLES + 0.2)
    finally:
        sampling.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sampling
        child.kill()
        await child.wait()

    assert monitor.percent >= 100 / (psutil.cpu_count() or 1) * SHARE_OF_A_BUSY_CORE
