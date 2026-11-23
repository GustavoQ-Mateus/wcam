import asyncio
import os
import select
import sys
from collections.abc import Callable
from typing import Protocol

POLL_SECONDS = 0.25
READ_BYTES = 4096


class PipeProbe(Protocol):
    def is_open(self) -> bool: ...


class PosixPipeProbe:
    def __init__(self, descriptor: int) -> None:
        self._descriptor = descriptor

    def is_open(self) -> bool:
        readable, _, _ = select.select([self._descriptor], [], [], 0)
        return not readable or os.read(self._descriptor, READ_BYTES) != b""


if sys.platform == "win32":
    import ctypes
    import msvcrt

    class WindowsPipeProbe:
        def __init__(self, descriptor: int) -> None:
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            self._peek = kernel.PeekNamedPipe
            self._peek.argtypes = [
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.c_uint32,
                ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint32),
                ctypes.c_void_p,
            ]
            self._peek.restype = ctypes.c_int
            self._handle = msvcrt.get_osfhandle(descriptor)

        def is_open(self) -> bool:
            available = ctypes.c_uint32(0)
            return bool(self._peek(self._handle, None, 0, None, ctypes.byref(available), None))


def pipe_probe(descriptor: int) -> PipeProbe:
    if sys.platform == "win32":
        return WindowsPipeProbe(descriptor)
    return PosixPipeProbe(descriptor)


async def stop_when_parent_closes(
    probe: PipeProbe,
    stop: Callable[[], None],
    poll_seconds: float = POLL_SECONDS,
) -> None:
    while True:
        if not probe.is_open():
            stop()
            return
        await asyncio.sleep(poll_seconds)
