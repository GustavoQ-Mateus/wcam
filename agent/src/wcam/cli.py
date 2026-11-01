import argparse
import asyncio
import io
import sys
from typing import TextIO

import segno

from wcam import __version__
from wcam.api.console_routes import pairing_url
from wcam.app import create_servers, phone_page_url, run
from wcam.config import Settings
from wcam.i18n import Messages, load_messages, resolve_language, system_language_tag
from wcam.media.peer import aiortc_peer_factory
from wcam.media.pipeline import FramePipeline
from wcam.media.quality import QualityMeter, read_y4m_luma
from wcam.network.certificates import TlsCertificate, load_or_create_certificate
from wcam.network.lan import NoLanInterfaceError, detect_lan_interface
from wcam.process_monitor import CpuMonitor
from wcam.services import AgentServices
from wcam.sessions.manager import SessionManager
from wcam.virtualcam.factory import create_sink
from wcam.virtualcam.sink import CameraState, SinkStatus

EXIT_NO_LAN = 2


def main() -> None:
    parser = argparse.ArgumentParser(prog="wcam")
    parser.add_argument("--version", action="version", version=f"wcam {__version__}")
    parser.parse_args()
    use_utf8_output(sys.stdout)
    settings = Settings()
    messages = load_messages(settings.locales_dir, resolve_language(system_language_tag()))
    try:
        lan = detect_lan_interface(settings.lan_ip)
    except NoLanInterfaceError:
        print(messages.text("terminal.no_lan"), file=sys.stderr)
        sys.exit(EXIT_NO_LAN)
    certificate = load_or_create_certificate(settings.data_dir, lan.ip)
    console_url = f"http://127.0.0.1:{settings.console_port}/"
    phone_url = phone_page_url(settings, lan)
    pipeline = FramePipeline(create_sink(settings.virtual_camera), quality_meter(settings))
    pipeline.open()
    manager = SessionManager(aiortc_peer_factory(lan.network, pipeline))
    services = AgentServices(manager, pipeline, CpuMonitor())
    ticket = manager.open_pairing()
    print_banner(messages, console_url, phone_url, certificate)
    print_virtual_camera(messages, pipeline.sink.status)
    print_pairing_qr(messages, pairing_url(phone_url, ticket.token))
    asyncio.run(run(create_servers(settings, lan, certificate, services), services))
    print(messages.text("terminal.stopped"))


def use_utf8_output(stream: TextIO) -> None:
    if isinstance(stream, io.TextIOWrapper):
        stream.reconfigure(encoding="utf-8")


def print_banner(messages: Messages, console_url: str, phone_url: str, certificate: TlsCertificate) -> None:
    print(messages.text("terminal.title", version=__version__))
    print(messages.text("terminal.console_address", url=console_url))
    print(messages.text("terminal.phone_address", url=phone_url))
    print(messages.text("terminal.fingerprint", fingerprint=certificate.fingerprint))


def quality_meter(settings: Settings) -> QualityMeter | None:
    if settings.quality_reference is None:
        return None
    return QualityMeter(read_y4m_luma(settings.quality_reference))


def print_virtual_camera(messages: Messages, status: SinkStatus) -> None:
    if status.state is CameraState.ACTIVE:
        print(messages.text("terminal.virtual_camera_active"))
        return
    reason = messages.text(f"console.virtual_camera_{status.reason}")
    print(messages.text("terminal.virtual_camera_unavailable", reason=reason))


def print_pairing_qr(messages: Messages, url: str) -> None:
    print(messages.text("terminal.scan_with_token"))
    print(messages.text("terminal.scan_hint"))
    segno.make(url, error="m").terminal(compact=True)
    print(messages.text("terminal.stop_hint"))
