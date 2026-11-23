import os
import socket
import subprocess
import sys
from pathlib import Path

import psutil
import pytest

from tests.integration.test_shutdown import EXIT_SECONDS, free_port, stopped_texts, wait_until_serving
from wcam.process_priority import ABOVE_NORMAL_PRIORITY_CLASS

CHILD = "import sys; sys.argv = ['wcam', '--child']; from wcam.cli import main; main()"
PARENT = (
    "import subprocess, sys, time; "
    "agent = subprocess.Popen(sys.argv[1:], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, "
    "stderr=subprocess.DEVNULL); "
    "print(agent.pid, flush=True); time.sleep(3600)"
)
EXIT_PORT_IN_USE = 3


def agent_environment(data_dir: Path, console_port: int) -> dict[str, str]:
    return {
        **os.environ,
        "WCAM_CONSOLE_PORT": str(console_port),
        "WCAM_PHONE_PORT": str(free_port()),
        "WCAM_VIRTUAL_CAMERA": "fake",
        "WCAM_DATA_DIR": str(data_dir),
        "PYTHONUNBUFFERED": "1",
    }


def start_child(data_dir: Path, console_port: int) -> subprocess.Popen[bytes]:
    return subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", CHILD],
        env=agent_environment(data_dir, console_port),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def process_tree_priorities(pid: int) -> list[int]:
    process = psutil.Process(pid)
    return [member.nice() for member in (process, *process.children(recursive=True))]


def finished_output(process: subprocess.Popen[bytes]) -> str:
    try:
        output, _ = process.communicate(timeout=EXIT_SECONDS)
    finally:
        if process.poll() is None:
            process.kill()
    return output.decode("utf-8", "replace")


def test_child_stops_cleanly_with_exit_code_zero_when_the_parent_closes_its_input(tmp_path: Path) -> None:
    console_port = free_port()
    process = start_child(tmp_path, console_port)
    wait_until_serving(console_port)
    assert process.stdin is not None

    process.stdin.close()
    text = finished_output(process)

    assert process.returncode == 0
    assert "Traceback" not in text
    assert text.strip().splitlines()[-1] in stopped_texts()


def test_child_stops_with_exit_code_zero_when_its_parent_dies(tmp_path: Path) -> None:
    console_port = free_port()
    parent = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", PARENT, sys.executable, "-c", CHILD],
        env=agent_environment(tmp_path, console_port),
        stdout=subprocess.PIPE,
    )
    assert parent.stdout is not None
    agent = psutil.Process(int(parent.stdout.readline()))
    try:
        wait_until_serving(console_port)

        parent.kill()
        parent.wait()

        assert agent.wait(timeout=EXIT_SECONDS) == 0
    finally:
        if parent.poll() is None:
            parent.kill()
        if agent.is_running():
            agent.kill()


def test_agent_whose_console_port_is_taken_exits_with_code_three(tmp_path: Path) -> None:
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        process = start_child(tmp_path, int(taken.getsockname()[1]))

        finished_output(process)

    assert process.returncode == EXIT_PORT_IN_USE


@pytest.mark.skipif(sys.platform != "win32", reason="process priority classes exist only on Windows")
def test_agent_runs_above_normal_priority(tmp_path: Path) -> None:
    console_port = free_port()
    process = start_child(tmp_path, console_port)
    try:
        wait_until_serving(console_port)

        priorities = process_tree_priorities(process.pid)
    finally:
        assert process.stdin is not None
        process.stdin.close()
        finished_output(process)

    assert ABOVE_NORMAL_PRIORITY_CLASS in priorities
