import io

from wcam.cli import use_utf8_output


def test_redirected_output_is_switched_to_utf8() -> None:
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

    use_utf8_output(stream)

    assert stream.encoding == "utf-8"
