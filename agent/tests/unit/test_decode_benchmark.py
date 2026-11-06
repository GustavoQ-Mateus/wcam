from wcam.tools.decode_benchmark import measure, table_row

SMALL_WIDTH = 320
SMALL_HEIGHT = 180
SMALL_FPS = 30
SMALL_SECONDS = 0.5


def test_small_format_is_decoded_and_measured() -> None:
    result = measure(SMALL_WIDTH, SMALL_HEIGHT, SMALL_FPS, SMALL_SECONDS)

    assert result.frames == round(SMALL_FPS * SMALL_SECONDS)
    assert result.milliseconds_per_frame > 0
    assert result.percent_of_one_core >= 0
    assert table_row(result).startswith(f"| {SMALL_WIDTH}x{SMALL_HEIGHT} | {SMALL_FPS} |")
