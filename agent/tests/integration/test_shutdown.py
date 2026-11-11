import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from wcam.config import Settings
from wcam.i18n import load_messages

STARTUP_SECONDS = 30.0
EXIT_SECONDS = 30.0
POLL_SECONDS = 0.2
SECOND_STOP_DELAY_SECONDS = 0.05
WINDOWS_CHILD = (
    "import ctypes, sys; ctypes.windll.kernel32.SetConsoleCtrlHandler(None, False); "
    "sys.argv = ['wcam']; from wcam.cli import main; main()"
)
POSIX_CHILD = "import sys; sys.argv = ['wcam']; from wcam.cli import main; main()"


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def start_agent(data_dir: Path) -> tuple[subprocess.Popen[bytes], int]:
    console_port = free_port()
    environment = {
        **os.environ,
        "WCAM_CONSOLE_PORT": str(console_port),
        "WCAM_PHONE_PORT": str(free_port()),
        "WCAM_VIRTUAL_CAMERA": "fake",
        "WCAM_DATA_DIR": str(data_dir),
        "PYTHONUNBUFFERED": "1",
    }
    if sys.platform == "win32":
        process = subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", WINDOWS_CHILD],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        process = subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", POSIX_CHILD],
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return process, console_port


def wait_until_serving(console_port: int) -> None:
    deadline = time.monotonic() + STARTUP_SECONDS
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{console_port}/api/health", timeout=1)
            return
        except OSError:
            time.sleep(POLL_SECONDS)
    raise TimeoutError


def press_ctrl_c(process: subprocess.Popen[bytes]) -> None:
    if sys.platform == "win32":
        os.kill(process.pid, signal.CTRL_C_EVENT)
    else:
        process.send_signal(signal.SIGINT)


def stopped_texts() -> set[str]:
    locales = Settings().locales_dir
    return {load_messages(locales, language).text("terminal.stopped") for language in ("en", "pt-BR")}


def test_ctrl_c_stops_with_only_the_stopped_message_and_exit_code_zero(tmp_path: Path) -> None:
    process, console_port = start_agent(tmp_path)
    try:
        wait_until_serving(console_port)
        press_ctrl_c(process)
        time.sleep(SECOND_STOP_DELAY_SECONDS)
        if process.poll() is None:
            press_ctrl_c(process)
        output, _ = process.communicate(timeout=EXIT_SECONDS)
    finally:
        if process.poll() is None:
            process.kill()
    text = output.decode("utf-8", "replace")

    assert process.returncode == 0
    assert "Traceback" not in text
    assert "KeyboardInterrupt" not in text
    assert text.strip().splitlines()[-1] in stopped_texts()
