import io
from pathlib import Path

import pytest
from PIL import Image

from tests.videos import SHORT_SECONDS, SMALL_HEIGHT, SMALL_WIDTH, chunks_of, small_video
from wcam.video.errors import NoVideoFileError, VideoTooLargeError, VideoUnsupportedError
from wcam.video.store import VideoStore, safe_file_name

TINY_LIMIT_BYTES = 10


def png_bytes() -> bytes:
    document = io.BytesIO()
    Image.new("RGB", (SMALL_WIDTH, SMALL_HEIGHT)).save(document, format="PNG")
    return document.getvalue()


async def test_stored_video_reports_its_metadata(tmp_path: Path) -> None:
    store = VideoStore(tmp_path / "video")
    data = small_video(tmp_path).read_bytes()

    stored = await store.save(chunks_of(data), "reunião.mp4")

    info = stored.info
    assert (info.name, info.width, info.height, info.fps, info.codec) == (
        "reunião.mp4",
        SMALL_WIDTH,
        SMALL_HEIGHT,
        30.0,
        "h264",
    )
    assert info.duration_seconds == pytest.approx(SHORT_SECONDS)
    assert stored.path.read_bytes() == data


@pytest.mark.parametrize("data", [b"this is not a video", png_bytes()])
async def test_file_that_is_not_a_video_is_refused_and_deleted(tmp_path: Path, data: bytes) -> None:
    store = VideoStore(tmp_path / "video")

    with pytest.raises(VideoUnsupportedError):
        await store.save(chunks_of(data), "notes.txt")

    assert list((tmp_path / "video").iterdir()) == []
    assert store.current is None


async def test_upload_above_the_limit_is_refused_and_deleted(tmp_path: Path) -> None:
    store = VideoStore(tmp_path / "video", max_bytes=TINY_LIMIT_BYTES)

    with pytest.raises(VideoTooLargeError):
        await store.save(chunks_of(small_video(tmp_path).read_bytes()), "big.mp4")

    assert list((tmp_path / "video").iterdir()) == []


async def test_new_video_replaces_the_previous_one(tmp_path: Path) -> None:
    store = VideoStore(tmp_path / "video")
    await store.save(chunks_of(small_video(tmp_path).read_bytes()), "first.mp4")

    await store.save(chunks_of(small_video(tmp_path, fps=15).read_bytes()), "second.mp4")

    assert [path.name for path in (tmp_path / "video").iterdir()] == ["second.mp4"]


async def test_stored_video_is_found_again_after_a_restart(tmp_path: Path) -> None:
    await VideoStore(tmp_path / "video").save(chunks_of(small_video(tmp_path).read_bytes()), "clip.mp4")
    restarted = VideoStore(tmp_path / "video")

    restarted.load()

    assert restarted.current is not None
    assert restarted.current.info.name == "clip.mp4"


async def test_removing_deletes_the_file_and_without_one_fails(tmp_path: Path) -> None:
    store = VideoStore(tmp_path / "video")
    await store.save(chunks_of(small_video(tmp_path).read_bytes()), "clip.mp4")

    store.remove()

    assert list((tmp_path / "video").iterdir()) == []
    with pytest.raises(NoVideoFileError):
        store.remove()


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("../../evil.mp4", "evil.mp4"),
        ("C:\\Users\\a\\clip.mov", "clip.mov"),
        ("a:b?.mp4", "a_b_.mp4"),
        ("..", "video"),
    ],
)
def test_file_name_never_leaves_the_video_folder(name: str, expected: str) -> None:
    assert safe_file_name(name) == expected
