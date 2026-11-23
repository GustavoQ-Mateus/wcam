import ctypes
import functools
import logging
import sys
import threading
from typing import Protocol

ABOVE_NORMAL_PRIORITY_CLASS = 0x00008000
PROCESS_POWER_THROTTLING = 4
POWER_THROTTLING_VERSION = 1
POWER_THROTTLING_EXECUTION_SPEED = 0x1
CAPTURE_TASK = "Capture"
SUCCESS = 0

logger = logging.getLogger(__name__)


class SchedulingCalls(Protocol):
    def set_above_normal_priority(self) -> int: ...

    def disable_power_throttling(self) -> int: ...

    def join_multimedia_task(self, task: str) -> int: ...


class ThreadMembership(threading.local):
    joined = False


class ProcessScheduling:
    def __init__(self, calls: SchedulingCalls | None) -> None:
        self._calls = calls
        self._membership = ThreadMembership()

    def raise_process(self) -> None:
        if self._calls is None:
            return
        error = self._calls.set_above_normal_priority()
        if error != SUCCESS:
            logger.warning("Could not raise the process priority (error %d)", error)
        error = self._calls.disable_power_throttling()
        if error != SUCCESS:
            logger.warning("Could not turn off power throttling (error %d)", error)

    def join_capture_task(self) -> None:
        if self._calls is None or self._membership.joined:
            return
        self._membership.joined = True
        error = self._calls.join_multimedia_task(CAPTURE_TASK)
        if error != SUCCESS:
            logger.warning("Could not join the %s multimedia task (error %d)", CAPTURE_TASK, error)


if sys.platform == "win32":

    class PowerThrottlingState(ctypes.Structure):
        _fields_ = (
            ("version", ctypes.c_uint32),
            ("control_mask", ctypes.c_uint32),
            ("state_mask", ctypes.c_uint32),
        )

    class WindowsSchedulingCalls:
        def __init__(self) -> None:
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            self._current_process = kernel.GetCurrentProcess
            self._current_process.argtypes = []
            self._current_process.restype = ctypes.c_void_p
            self._set_priority_class = kernel.SetPriorityClass
            self._set_priority_class.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            self._set_priority_class.restype = ctypes.c_int
            self._set_process_information = kernel.SetProcessInformation
            self._set_process_information.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32]
            self._set_process_information.restype = ctypes.c_int
            avrt = ctypes.WinDLL("avrt", use_last_error=True)
            self._join_task = avrt.AvSetMmThreadCharacteristicsW
            self._join_task.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32)]
            self._join_task.restype = ctypes.c_void_p

        def set_above_normal_priority(self) -> int:
            succeeded = self._set_priority_class(self._current_process(), ABOVE_NORMAL_PRIORITY_CLASS)
            return SUCCESS if succeeded else ctypes.get_last_error()

        def disable_power_throttling(self) -> int:
            state = PowerThrottlingState(POWER_THROTTLING_VERSION, POWER_THROTTLING_EXECUTION_SPEED, 0)
            succeeded = self._set_process_information(
                self._current_process(),
                PROCESS_POWER_THROTTLING,
                ctypes.byref(state),
                ctypes.sizeof(state),
            )
            return SUCCESS if succeeded else ctypes.get_last_error()

        def join_multimedia_task(self, task: str) -> int:
            task_index = ctypes.c_uint32(0)
            handle = self._join_task(task, ctypes.byref(task_index))
            return SUCCESS if handle else ctypes.get_last_error()


@functools.cache
def system_scheduling() -> ProcessScheduling:
    if sys.platform == "win32":
        return ProcessScheduling(WindowsSchedulingCalls())
    return ProcessScheduling(None)


def raise_process_priority() -> None:
    system_scheduling().raise_process()


def join_capture_task() -> None:
    system_scheduling().join_capture_task()
