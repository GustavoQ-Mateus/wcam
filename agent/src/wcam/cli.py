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
from wcam.media.color_calibration import IDENTITY_TABLE
from wcam.media.color_calibrator import ColorCalibrator
from wcam.media.color_trace import ColorTrace
from wcam.media.episodes import open_episode_log
from wcam.media.peer import aiortc_peer_factory
from wcam.media.pipeline import FramePipeline
from wcam.media.quality import QualityMeter, read_y4m_luma
from wcam.network.certificates import TlsCertificate, load_or_create_certificate
from wcam.network.lan import NoLanInterfaceError, detect_lan_interface
from wcam.process_monitor import CpuMonitor
from wcam.services import AgentServices
from wcam.sessions.comparisons import CalibrationSnapshot, ComparisonStore
from wcam.sessions.manager import SessionManager
from wcam.virtualcam.factory import FallbackReason, SinkSelection, select_sink
from wcam.virtualcam.media_foundation_sink import load_native_library
from wcam.virtualcam.sink import CameraState

EXIT_NO_LAN = 2
OBS_FALLBACK_REASONS = (
    FallbackReason.NATIVE_NOT_REGISTERED,
    FallbackReason.WINDOWS_TOO_OLD,
    FallbackReason.NATIVE_ERROR,
)


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
    open_episode_log(settings.data_dir)
    console_url = f"http://127.0.0.1:{settings.console_port}/"
    phone_url = phone_page_url(settings, lan)
    selection = select_sink(settings.virtual_camera, lambda: load_native_library(settings.vcam_dll))
    pipeline = FramePipeline(
        selection.sink,
        quality_meter(settings),
        fallback_reason=selection.fallback_reason,
        color_calibrator=color_calibrator(settings),
    )
    pipeline.open()
    comparisons = ComparisonStore(lambda: calibration_snapshot(pipeline)) if settings.dev_tools else None
    manager = SessionManager(aiortc_peer_factory(lan.network, pipeline), comparisons=comparisons)
    services = AgentServices(manager, pipeline, CpuMonitor(), comparisons)
    print_banner(messages, console_url, phone_url, certificate)
    print_virtual_camera(messages, selection)
    announce_pairing(messages, manager, phone_url, console_url, sys.stdout)
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


def color_calibrator(settings: Settings) -> ColorCalibrator:
    trace = None if settings.color_trace_dir is None else ColorTrace(settings.color_trace_dir)
    return ColorCalibrator(trace)


def calibration_snapshot(pipeline: FramePipeline) -> CalibrationSnapshot:
    status = pipeline.color_calibrator.status
    luma_table, chroma_table = pipeline.color_tables() or (IDENTITY_TABLE, IDENTITY_TABLE)
    return CalibrationSnapshot(status.state.value, status.delta_e, luma_table, chroma_table)


def print_virtual_camera(messages: Messages, selection: SinkSelection) -> None:
    if selection.fallback_reason in OBS_FALLBACK_REASONS:
        print(messages.text("terminal.virtual_camera_fallback"))
    status = selection.sink.status
    if status.state is CameraState.ACTIVE:
        print(messages.text("terminal.virtual_camera_active", name=selection.sink.name))
        return
    reason = messages.text(f"console.virtual_camera_{status.reason}")
    print(messages.text("terminal.virtual_camera_unavailable", reason=reason))


def announce_pairing(
    messages: Messages,
    manager: SessionManager,
    phone_url: str,
    console_url: str,
    output: TextIO,
) -> None:
    if output.isatty():
        print_pairing_qr(messages, pairing_url(phone_url, manager.open_pairing().token), output)
    else:
        print(messages.text("terminal.scan_in_console", url=console_url), file=output)
    print(messages.text("terminal.stop_hint"), file=output)


def print_pairing_qr(messages: Messages, url: str, output: TextIO) -> None:
    print(messages.text("terminal.scan_with_token"), file=output)
    print(messages.text("terminal.scan_hint"), file=output)
    segno.make(url, error="m").terminal(out=output, compact=True)
