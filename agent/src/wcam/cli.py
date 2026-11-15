import argparse
import asyncio
import contextlib
import io
import logging
import sys
import webbrowser
from typing import TextIO

import segno

from wcam import __version__
from wcam.api.console_routes import pairing_url
from wcam.app import create_servers, phone_page_url, request_stop, run, stop_signals_handled
from wcam.config import Settings
from wcam.diagnostics.dev_events import EpisodeEvents
from wcam.i18n import Messages, load_messages, resolve_language, system_language_tag
from wcam.media.camera_format import CameraFormatControl
from wcam.media.color_correction import IDENTITY_TABLE, CorrectionState, DisplayConvention
from wcam.media.decode_timing import time_decoders
from wcam.media.episodes import EPISODE_LOGGER, open_episode_log
from wcam.media.peer import aiortc_peer_factory
from wcam.media.pipeline import FramePipeline
from wcam.media.quality import QualityMeter, read_y4m_luma
from wcam.network.certificates import TlsCertificate, load_or_create_certificate
from wcam.network.lan import NoLanInterfaceError, detect_lan_interface
from wcam.process_monitor import CpuMonitor
from wcam.services import AgentServices
from wcam.sessions.comparisons import ComparisonStore, CorrectionSnapshot
from wcam.sessions.manager import SessionManager, SessionState
from wcam.tray.tray import Tray, windows_tray_icon
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
    with contextlib.suppress(KeyboardInterrupt):
        start(settings, messages)
    print(messages.text("terminal.stopped"))


def start(settings: Settings, messages: Messages) -> None:
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
    )
    pipeline.open()
    comparisons = ComparisonStore(lambda: correction_snapshot(pipeline)) if settings.dev_tools else None
    camera = CameraFormatControl(pipeline)
    manager = SessionManager(
        aiortc_peer_factory(lan.network, pipeline),
        comparisons=comparisons,
        camera=camera,
        output=pipeline,
    )
    services = AgentServices(manager, pipeline, CpuMonitor(), camera, comparisons)
    time_decoders(pipeline.stage_times.record_decode)
    logging.getLogger(EPISODE_LOGGER).addHandler(EpisodeEvents(services.dev_events))
    print_banner(messages, console_url, phone_url, certificate)
    print_virtual_camera(messages, selection)
    announce_pairing(messages, manager, phone_url, console_url, sys.stdout)
    hint_confirmation(messages, manager, sys.stdout)
    servers = create_servers(settings, lan, certificate, services)
    icon = windows_tray_icon()
    tray = None
    if icon is not None:
        tray = Tray(icon, services, messages, lambda: webbrowser.open(console_url), lambda: request_stop(servers))
    with stop_signals_handled(servers):
        asyncio.run(run(servers, services, None if tray is None else tray.run))


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


def correction_snapshot(pipeline: FramePipeline) -> CorrectionSnapshot:
    correction = pipeline.color_correction
    luma_table, chroma_table = pipeline.color_tables() or (IDENTITY_TABLE, IDENTITY_TABLE)
    if correction is None:
        return CorrectionSnapshot(CorrectionState.DEFAULT, None, DisplayConvention.STANDARD, luma_table, chroma_table)
    return CorrectionSnapshot(correction.state, correction.transfer, correction.display, luma_table, chroma_table)


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


def hint_confirmation(messages: Messages, manager: SessionManager, output: TextIO) -> None:
    hinted: set[str] = set()

    def hint() -> None:
        session = manager.status().session
        if session is None or session.state is not SessionState.AWAITING_CONFIRMATION or session.id in hinted:
            return
        hinted.add(session.id)
        print(messages.text("terminal.confirm_hint"), file=output)

    manager.on_change(hint)


def print_pairing_qr(messages: Messages, url: str, output: TextIO) -> None:
    print(messages.text("terminal.scan_with_token"), file=output)
    print(messages.text("terminal.scan_hint"), file=output)
    segno.make(url, error="m").terminal(out=output, compact=True)
