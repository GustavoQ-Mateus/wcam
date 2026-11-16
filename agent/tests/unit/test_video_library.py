import asyncio
from pathlib import Path

import numpy as np
import pytest

from tests.videos import chunks_of, small_video
from wcam.persistence.database import open_database
from wcam.video.errors import VideoLibraryFullError, VideoTooLargeError
from wcam.video.filmstrip import Thumbnail, evenly_spaced
from wcam.video.library import VideoLibrary, file_suffix

TINY_LIMIT_BYTES = 10
THUMBNAIL_SHAPE = (9, 16, 3)


def library_in(tmp_path: Path, **limits: int) -> VideoLibrary:
    return VideoLibrary(tmp_path / "video", open_database(tmp_path / "data"), **limits)


async def video_bytes(tmp_path: Path) -> bytes:
    return await asyncio.to_thread(small_video(tmp_path).read_bytes)


def folder_files(folder: Path) -> list[str]:
    return sorted(path.name for path in folder.iterdir())


async def test_full_library_refuses_another_video_without_writing_it(tmp_path: Path) -> None:
    library = library_in(tmp_path, max_videos=1)
    await library.add(chunks_of(await video_bytes(tmp_path)), "first.mp4")
    before = folder_files(tmp_path / "video")

    with pytest.raises(VideoLibraryFullError):
        await library.add(chunks_of(await video_bytes(tmp_path)), "second.mp4")

    assert folder_files(tmp_path / "video") == before


async def test_upload_above_the_limit_is_refused_and_deleted(tmp_path: Path) -> None:
    library = library_in(tmp_path, max_bytes=TINY_LIMIT_BYTES)

    with pytest.raises(VideoTooLargeError):
        await library.add(chunks_of(await video_bytes(tmp_path)), "big.mp4")

    assert folder_files(tmp_path / "video") == []


async def test_loading_drops_files_of_no_video_and_videos_without_a_file(tmp_path: Path) -> None:
    library = library_in(tmp_path)
    kept = await library.add(chunks_of(await video_bytes(tmp_path)), "kept.mp4")
    lost = await library.add(chunks_of(await video_bytes(tmp_path)), "lost.mp4")
    lost.path.unlink()
    (tmp_path / "video" / "reunião.mp4").write_bytes(b"single file of the first revision")
    (tmp_path / "video" / ".upload-0123").write_bytes(b"interrupted")
    restarted = library_in(tmp_path)

    restarted.load()

    assert [video.id for video in restarted.videos] == [kept.id]
    assert folder_files(tmp_path / "video") == sorted([kept.path.name, kept.filmstrip_path.name])


def test_migrations_run_once_and_keep_the_data(tmp_path: Path) -> None:
    database = open_database(tmp_path)
    database.execute("insert into videos values ('v1', 'a.mp4', 'v1.mp4', 2.0, 320, 180, 30.0, 'h264', 2, 1)")

    reopened = open_database(tmp_path)

    assert reopened.execute("pragma user_version").fetchone() == (1,)
    assert reopened.execute("select id from videos").fetchall() == [("v1",)]


@pytest.mark.parametrize(
    ("name", "suffix"), [("clip.MOV", ".mov"), ("C:\\Users\\a\\clip.mp4", ".mp4"), ("notes", ""), ("x.m p4", "")]
)
def test_stored_file_keeps_only_a_safe_extension(name: str, suffix: str) -> None:
    assert file_suffix(name) == suffix


def test_filmstrip_takes_the_keyframe_nearest_each_evenly_spaced_point() -> None:
    keyframes: list[tuple[float, Thumbnail]] = [
        (float(index), np.full(THUMBNAIL_SHAPE, index, dtype=np.uint8)) for index in range(4)
    ]

    chosen = evenly_spaced(keyframes, 4.0, 2)

    assert [int(image[0, 0, 0]) for image in chosen] == [1, 3]
