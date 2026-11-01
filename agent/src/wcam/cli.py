import argparse
import asyncio
import io
import sys
from typing import TextIO

import segno

from wcam import __version__
from wcam.app import create_servers, serve
from wcam.config import Settings
from wcam.i18n import Messages, load_messages, resolve_language, system_language_tag
from wcam.network.certificates import TlsCertificate, load_or_create_certificate
from wcam.network.lan import NoLanInterfaceError, detect_lan_interface

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
    phone_url = f"https://{lan.ip}:{settings.phone_port}/cam"
    print_banner(messages, console_url, phone_url, certificate)
    asyncio.run(serve(create_servers(settings, lan, certificate)))
    print(messages.text("terminal.stopped"))


def use_utf8_output(stream: TextIO) -> None:
    if isinstance(stream, io.TextIOWrapper):
        stream.reconfigure(encoding="utf-8")


def print_banner(messages: Messages, console_url: str, phone_url: str, certificate: TlsCertificate) -> None:
    print(messages.text("terminal.title", version=__version__))
    print(messages.text("terminal.console_address", url=console_url))
    print(messages.text("terminal.phone_address", url=phone_url))
    print(messages.text("terminal.fingerprint", fingerprint=certificate.fingerprint))
    print(messages.text("terminal.scan_hint"))
    segno.make(phone_url, error="m").terminal(compact=True)
    print(messages.text("terminal.stop_hint"))
