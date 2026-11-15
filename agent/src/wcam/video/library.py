import asyncio
import logging
import re
import secrets
import sqlite3
from collections.abc import AsyncIterable
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import BinaryIO

import av
from av.container import InputContainer
from av.error import FFmpegError
from av.video.stream import VideoStream

from wcam.persistence.database import transaction
from wcam.video.errors import (
    VideoLibraryFullError,
    VideoNotFoundError,
    VideoTooLargeError,
    VideoUnsupportedError,
)
from wcam.video.filmstrip import write_filmstrip
from wcam.video.frames import shown_size

MAX_VIDEO_BYTES = 20 * 1024**3
MAX_VIDEOS = 20
WRITE_BUFFER_BYTES = 4 * 1024 * 1024
UPLOAD_PREFIX = ".upload-"
VIDEO_ID_BYTES = 8
FILMSTRIP_SUFFIX = ".filmstrip.jpg"
MAX_SUFFIX_LENGTH = 10
SAFE_SUFFIX = re.compile(r"^\.[A-Za-z0-9]+$")
FPS_DECIMALS = 2
DURATION_DECIMALS = 3
DROPPED_FILE = "Removed a file in the video folder that belongs to no stored video"
DROPPED_VIDEO = "Forgot a stored video whose file is missing"
UNDECODABLE = (FFmpegError, IndexError, StopIteration, OSError, ValueError)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class VideoFileInfo:
    name: str
    duration_seconds: float
    width: int
    height: int
    fps: float
    codec: str


@dataclass(frozen=True, slots=True)
class LibraryVideo:
    id: str
    path: Path
    info: VideoFileInfo
    filmstrip_frames: int

    @property
    def filmstrip_path(self) -> Path:
        return self.path.with_name(f"{self.id}{FILMSTRIP_SUFFIX}")


class VideoLibrary:
    def __init__(
        self,
        directory: Path,
        database: sqlite3.Connection,
        max_bytes: int = MAX_VIDEO_BYTES,
        max_videos: int = MAX_VIDEOS,
    ) -> None:
        self._directory = directory
        self._database = database
        self._max_bytes = max_bytes
        self._max_videos = max_videos
        self._videos: dict[str, LibraryVideo] = {}

    @property
    def videos(self) -> tuple[LibraryVideo, ...]:
        return tuple(self._videos.values())

    def find(self, video_id: str) -> LibraryVideo:
        video = self._videos.get(video_id)
        if video is None:
            raise VideoNotFoundError
        return video

    def ensure_room(self) -> None:
        if len(self._videos) >= self._max_videos:
            raise VideoLibraryFullError

    def load(self) -> None:
        for video in self._stored_videos():
            if video.path.is_file() and video.filmstrip_path.is_file():
                self._videos[video.id] = video
            else:
                logger.warning(DROPPED_VIDEO)
                self._forget(video.id)
        self._remove_stray_files()

    async def add(self, chunks: AsyncIterable[bytes], name: str) -> LibraryVideo:
        self.ensure_room()
        self._directory.mkdir(parents=True, exist_ok=True)
        video_id = secrets.token_hex(VIDEO_ID_BYTES)
        upload = self._directory / f"{UPLOAD_PREFIX}{video_id}"
        filmstrip = self._directory / f"{video_id}{FILMSTRIP_SUFFIX}"
        try:
            await self._write(chunks, upload)
            info, frames = await asyncio.to_thread(examined_video, upload, name, filmstrip)
        except BaseException:
            upload.unlink(missing_ok=True)
            filmstrip.unlink(missing_ok=True)
            raise
        path = upload.replace(self._directory / f"{video_id}{file_suffix(name)}")
        stored = LibraryVideo(video_id, path, info, frames)
        self._insert(stored)
        self._videos[video_id] = stored
        return stored

    def remove(self, video_id: str) -> None:
        video = self.find(video_id)
        self._forget(video_id)
        del self._videos[video_id]
        video.path.unlink(missing_ok=True)
        video.filmstrip_path.unlink(missing_ok=True)

    def _stored_videos(self) -> list[LibraryVideo]:
        rows = self._database.execute(
            """
            select
                id,
                file_name,
                name,
                duration_seconds,
                width,
                height,
                fps,
                codec,
                filmstrip_frames
            from videos
            order by added_order
            """
        ).fetchall()
        return [LibraryVideo(row[0], self._directory / row[1], VideoFileInfo(*row[2:8]), row[8]) for row in rows]

    def _insert(self, video: LibraryVideo) -> None:
        info = video.info
        with transaction(self._database) as database:
            database.execute(
                """
                insert into videos (
                    id,
                    name,
                    file_name,
                    duration_seconds,
                    width,
                    height,
                    fps,
                    codec,
                    filmstrip_frames,
                    added_order
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, (select coalesce(max(added_order), 0) + 1 from videos))
                """,
                (
                    video.id,
                    info.name,
                    video.path.name,
                    info.duration_seconds,
                    info.width,
                    info.height,
                    info.fps,
                    info.codec,
                    video.filmstrip_frames,
                ),
            )

    def _forget(self, video_id: str) -> None:
        with transaction(self._database) as database:
            database.execute("delete from videos where id = ?", (video_id,))

    def _remove_stray_files(self) -> None:
        if not self._directory.is_dir():
            return
        kept = {path.name for video in self._videos.values() for path in (video.path, video.filmstrip_path)}
        for path in self._directory.iterdir():
            if path.is_file() and path.name not in kept:
                logger.warning(DROPPED_FILE)
                path.unlink(missing_ok=True)

    async def _write(self, chunks: AsyncIterable[bytes], upload: Path) -> None:
        written = 0
        buffer = bytearray()
        with upload.open("wb") as file:
            async for chunk in chunks:
                written += len(chunk)
                if written > self._max_bytes:
                    raise VideoTooLargeError
                buffer += chunk
                if len(buffer) >= WRITE_BUFFER_BYTES:
                    buffer = await flushed(file, buffer)
            await flushed(file, buffer)


async def flushed(file: BinaryIO, buffer: bytearray) -> bytearray:
    await asyncio.to_thread(file.write, buffer)
    return bytearray()


def file_suffix(name: str) -> str:
    suffix = Path(name.replace("\\", "/").rsplit("/", 1)[-1]).suffix.lower()
    return suffix if len(suffix) <= MAX_SUFFIX_LENGTH and SAFE_SUFFIX.match(suffix) else ""


def examined_video(path: Path, name: str, filmstrip: Path) -> tuple[VideoFileInfo, int]:
    info = probe_video(path, name)
    try:
        return info, write_filmstrip(path, filmstrip, info.duration_seconds)
    except UNDECODABLE as error:
        raise VideoUnsupportedError from error


def probe_video(path: Path, name: str) -> VideoFileInfo:
    try:
        with av.open(str(path)) as container:
            return video_info(container, name)
    except UNDECODABLE as error:
        raise VideoUnsupportedError from error


def video_info(container: InputContainer, name: str) -> VideoFileInfo:
    stream = container.streams.video[0]
    first = next(container.decode(stream))
    duration = duration_seconds(container, stream)
    if duration <= 0:
        raise VideoUnsupportedError
    width, height = shown_size(first)
    rate = stream.average_rate or stream.guessed_rate or Fraction(0)
    return VideoFileInfo(
        name=name,
        duration_seconds=round(duration, DURATION_DECIMALS),
        width=width,
        height=height,
        fps=round(float(rate), FPS_DECIMALS),
        codec=stream.codec_context.name,
    )


def duration_seconds(container: InputContainer, stream: VideoStream) -> float:
    if stream.duration is not None and stream.time_base is not None:
        return float(stream.duration * stream.time_base)
    if container.duration is not None:
        return container.duration / av.time_base
    return 0.0
