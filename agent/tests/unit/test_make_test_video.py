import sys
from pathlib import Path

import pytest

from wcam.tools.make_test_video import DEFAULT_HEIGHT, DEFAULT_WIDTH, PORTRAIT_ARGUMENT, PORTRAIT_SECONDS, main
from wcam.video.store import probe_video


def test_portrait_argument_writes_an_upright_video_turned_like_a_phone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "portrait.mp4"
    monkeypatch.setattr(sys, "argv", ["make_test_video", str(path), PORTRAIT_ARGUMENT])

    main()

    info = probe_video(path, path.name)
    assert (info.width, info.height, info.duration_seconds) == (DEFAULT_HEIGHT, DEFAULT_WIDTH, PORTRAIT_SECONDS)
