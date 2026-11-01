import io

import pytest

from wcam.cli import print_pairing_qr, use_utf8_output
from wcam.config import Settings
from wcam.i18n import load_messages


def test_redirected_output_is_switched_to_utf8() -> None:
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

    use_utf8_output(stream)

    assert stream.encoding == "utf-8"


def test_pairing_qr_is_announced_with_token_and_certificate_hints(capsys: pytest.CaptureFixture[str]) -> None:
    messages = load_messages(Settings().locales_dir, "en")

    print_pairing_qr(messages, "https://192.168.0.10:8443/cam#t=secret-token")

    output = capsys.readouterr().out
    assert output.splitlines()[:2] == [messages.text("terminal.scan_with_token"), messages.text("terminal.scan_hint")]
    assert "secret-token" not in output
