import asyncio
import subprocess
from pathlib import Path

import httpx
import psutil
import pytest

from tests.integration.test_child_mode import agent_environment, finished_output
from tests.integration.test_shutdown import free_port, wait_until_serving
from tests.integration.test_video_source_api import uploaded, video_status, whole_clip
from tests.integration.test_webrtc import (
    POLL_SECONDS,
    WAIT_SECONDS,
    confirm_on_both_sides,
    paired_phone,
    phone_client_peer,
    trusting,
)
from tests.videos import small_video
from wcam.network.certificates import load_or_create_certificate
from wcam.network.lan import detect_lan_interface

PACKAGED_AGENT = Path(__file__).resolve().parents[2] / "dist" / "wcam" / "wcam.exe"

pytestmark = pytest.mark.skipif(
    not PACKAGED_AGENT.is_file(), reason="build the agent with: uv run pyinstaller packaging/wcam.spec"
)


def start_packaged_child(data_dir: Path, console_port: int, phone_port: int) -> subprocess.Popen[bytes]:
    environment = agent_environment(data_dir, console_port) | {"WCAM_PHONE_PORT": str(phone_port)}
    return subprocess.Popen(  # noqa: S603
        [str(PACKAGED_AGENT), "--child"],
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


async def decoder_in_use(console: httpx.AsyncClient) -> str | None:
    async with asyncio.timeout(WAIT_SECONDS):
        while True:
            decoder: str | None = (await video_status(console))["decoder"]
            if decoder is not None:
                return decoder
            await asyncio.sleep(POLL_SECONDS)


async def decode_the_video_with_a_live_phone(data_dir: Path, console_port: int, phone_port: int) -> str | None:
    lan = detect_lan_interface(None)
    certificate = load_or_create_certificate(data_dir, lan.ip)
    client = phone_client_peer()
    async with (
        httpx.AsyncClient(base_url=f"http://127.0.0.1:{console_port}") as console,
        httpx.AsyncClient(
            base_url=f"https://{lan.ip}:{phone_port}", verify=trusting(certificate.certificate_path)
        ) as phone,
    ):
        try:
            await paired_phone(console, phone, client)
            await confirm_on_both_sides(console, client, phone_first=False)
            assert (await client.next_state())["state"] == "live"
            video = await uploaded(console, small_video(data_dir))
            await console.put("/api/timeline", json={"clips": [whole_clip(video)]})
            await console.put("/api/video-source", json={"active": True})
            return await decoder_in_use(console)
        finally:
            await client.connection.close()


def test_packaged_agent_decodes_the_video_on_the_video_card_in_its_own_child_process(tmp_path: Path) -> None:
    console_port = free_port()
    phone_port = free_port()
    process = start_packaged_child(tmp_path, console_port, phone_port)
    try:
        wait_until_serving(console_port)
        decoder = asyncio.run(decode_the_video_with_a_live_phone(tmp_path, console_port, phone_port))
        children = [Path(child.exe()) for child in psutil.Process(process.pid).children(recursive=True)]
    finally:
        assert process.stdin is not None
        process.stdin.close()
        finished_output(process)

    assert decoder == "hardware"
    assert PACKAGED_AGENT in children
    assert process.returncode == 0
