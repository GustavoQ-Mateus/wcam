import io

from tests.fakes import FakePeerFactory
from tests.unit.test_session_manager import session_request
from wcam.cli import announce_pairing, hint_confirmation, use_utf8_output
from wcam.config import Settings
from wcam.i18n import Messages, load_messages
from wcam.sessions.manager import SessionManager

PHONE_URL = "https://192.168.0.10:8443/cam"
CONSOLE_URL = "http://127.0.0.1:8080/"


class TerminalOutput(io.StringIO):
    def isatty(self) -> bool:
        return True


def english() -> Messages:
    return load_messages(Settings().locales_dir, "en")


def test_redirected_output_is_switched_to_utf8() -> None:
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

    use_utf8_output(stream)

    assert stream.encoding == "utf-8"


def test_terminal_shows_the_qr_code_with_token_and_certificate_hints() -> None:
    manager = SessionManager(FakePeerFactory())
    output = TerminalOutput()

    announce_pairing(english(), manager, PHONE_URL, CONSOLE_URL, output)

    lines = output.getvalue().splitlines()
    assert lines[:2] == [english().text("terminal.scan_with_token"), english().text("terminal.scan_hint")]
    assert manager.status().pairing_expires_at is not None
    assert "#t=" not in output.getvalue()


def test_redirected_output_gets_the_console_address_and_no_pairing_link() -> None:
    manager = SessionManager(FakePeerFactory())
    output = io.StringIO()

    announce_pairing(english(), manager, PHONE_URL, CONSOLE_URL, output)

    assert output.getvalue().splitlines() == [
        english().text("terminal.scan_in_console", url=CONSOLE_URL),
        english().text("terminal.stop_hint"),
    ]
    assert "#t=" not in output.getvalue()
    assert manager.status().pairing_expires_at is None


async def test_terminal_says_where_to_confirm_once_when_the_phone_connects() -> None:
    factory = FakePeerFactory()
    manager = SessionManager(factory)
    output = io.StringIO()
    hint_confirmation(english(), manager, output)
    await manager.create_session(session_request(manager.open_pairing().token))

    factory.last.events.on_connected()
    manager.confirm()

    assert output.getvalue().splitlines() == [english().text("terminal.confirm_hint")]
