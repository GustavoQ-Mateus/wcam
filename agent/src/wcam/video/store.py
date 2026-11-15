import asyncio
import logging
import re
import secrets
from collections.abc import AsyncIterable
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import BinaryIO

import av
from av.container import InputContainer
from av.error import FFmpegError
from av.video.stream import VideoStream

from wcam.video.errors import NoVideoFileError, VideoTooLargeError, VideoUnsupportedError
from wcam.video.frames import shown_size

MAX_VIDEO_BYTES = 20 * 1024**3
WRITE_BUFFER_BYTES = 4 * 1024 * 1024
UPLOAD_PREFIX = ".upload-"
UPLOAD_ID_BYTES = 8
FALLBACK_NAME = "video"
UNSAFE_NAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
FPS_DECIMALS = 2
DURATION_DECIMALS = 3
DROPPED_STORED_VIDEO = "Removed a stored video the agent can no longer decode"
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
class StoredVideo:
    path: Path
    info: VideoFileInfo


class VideoStore:
    def __init__(self, directory: Path, max_bytes: int = MAX_VIDEO_BYTES) -> None:
        self._directory = directory
        self._max_bytes = max_bytes
        self._current: StoredVideo | None = None

    @property
    def current(self) -> StoredVideo | None:
        return self._current

    def load(self) -> None:
        if not self._directory.is_dir():
            return
        for path in sorted(self._directory.iterdir()):
            self._load_file(path)

    async def save(self, chunks: AsyncIterable[bytes], name: str) -> StoredVideo:
        self._directory.mkdir(parents=True, exist_ok=True)
        upload = self._directory / f"{UPLOAD_PREFIX}{secrets.token_hex(UPLOAD_ID_BYTES)}"
        try:
            await self._write(chunks, upload)
            info = await asyncio.to_thread(probe_video, upload, name)
        except BaseException:
            upload.unlink(missing_ok=True)
            raise
        self._delete_current()
        target = self._directory / safe_file_name(name)
        upload.replace(target)
        self._current = StoredVideo(target, info)
        return self._current

    def remove(self) -> None:
        if self._current is None:
            raise NoVideoFileError
        self._delete_current()

    def _load_file(self, path: Path) -> None:
        if not path.is_file():
            return
        if path.name.startswith(UPLOAD_PREFIX) or self._current is not None:
            path.unlink(missing_ok=True)
            return
        try:
            self._current = StoredVideo(path, probe_video(path, path.name))
        except VideoUnsupportedError:
            logger.warning(DROPPED_STORED_VIDEO)
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

    def _delete_current(self) -> None:
        if self._current is not None:
            self._current.path.unlink(missing_ok=True)
        self._current = None


async def flushed(file: BinaryIO, buffer: bytearray) -> bytearray:
    await asyncio.to_thread(file.write, buffer)
    return bytearray()


def safe_file_name(name: str) -> str:
    last_part = name.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = UNSAFE_NAME_CHARACTERS.sub("_", last_part).strip(" .")
    return cleaned or FALLBACK_NAME


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
