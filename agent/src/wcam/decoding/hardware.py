import contextlib
import multiprocessing
import threading
import time
from dataclasses import dataclass
from multiprocessing.shared_memory import SharedMemory
from typing import Protocol, cast

import numpy as np
from av import VideoFrame

from wcam.decoding.child import i420_bytes, serve
from wcam.decoding.messages import (
    ChildReply,
    DecodedImage,
    DecodeFailed,
    EncodedPacket,
    OpenStream,
    PacketDecoded,
    StreamOpened,
)
from wcam.decoding.status import FallbackReason

LARGEST_WIDTH = 3840
LARGEST_HEIGHT = 2160
SLOT_BYTES = i420_bytes(LARGEST_WIDTH, LARGEST_HEIGHT)
SLOT_COUNT = 4
OPEN_TIMEOUT_SECONDS = 15.0
REPLY_TIMEOUT_SECONDS = 2.0
STOP_TIMEOUT_SECONDS = 2.0
I420_FORMAT = "yuv420p"
PROCESS_NAME = "wcam-decoder"
MILLISECONDS_PER_SECOND = 1000


class HardwareDecodeError(Exception):
    def __init__(self, reason: FallbackReason) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class HardwareFrames:
    frames: list[VideoFrame]
    decode_milliseconds: float
    transfer_milliseconds: float


class KeyFrameFlag(Protocol):
    key_frame: bool


class HardwareDecoder(Protocol):
    def open(self, codec: str, extradata: bytes | None) -> FallbackReason | None: ...

    def decode(self, packet: EncodedPacket) -> HardwareFrames: ...

    def close(self) -> None: ...


class HardwareDecoderProcess:
    def __init__(self) -> None:
        context = multiprocessing.get_context("spawn")
        self._lock = threading.Lock()
        self._closed = False
        self._memory = SharedMemory(create=True, size=SLOT_BYTES * SLOT_COUNT)
        self._connection, child_end = context.Pipe()
        self._process = context.Process(
            target=serve,
            args=(child_end, self._memory.name, SLOT_BYTES, SLOT_COUNT),
            name=PROCESS_NAME,
            daemon=True,
        )
        self._process.start()
        child_end.close()

    def open(self, codec: str, extradata: bytes | None) -> FallbackReason | None:
        with self._lock:
            try:
                reply = self._exchange(OpenStream(codec, extradata), OPEN_TIMEOUT_SECONDS)
            except HardwareDecodeError:
                return FallbackReason.OPEN_FAILED
        return reply.failure if isinstance(reply, StreamOpened) else FallbackReason.OPEN_FAILED

    def decode(self, packet: EncodedPacket) -> HardwareFrames:
        with self._lock:
            reply = self._exchange(packet, REPLY_TIMEOUT_SECONDS)
            if isinstance(reply, DecodeFailed):
                raise HardwareDecodeError(reply.failure)
            if not isinstance(reply, PacketDecoded):
                raise HardwareDecodeError(FallbackReason.STREAM_ERROR)
            started = time.perf_counter()
            frames = [self._frame(image) for image in reply.images]
        copy_milliseconds = (time.perf_counter() - started) * MILLISECONDS_PER_SECOND
        return HardwareFrames(frames, reply.decode_milliseconds, reply.transfer_milliseconds + copy_milliseconds)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._stop_child()
            self._connection.close()
            self._memory.close()
            self._memory.unlink()

    def _exchange(self, request: OpenStream | EncodedPacket, timeout_seconds: float) -> ChildReply:
        if self._closed:
            raise HardwareDecodeError(FallbackReason.STREAM_ERROR)
        try:
            self._connection.send(request)
            if not self._connection.poll(timeout_seconds):
                self._process.kill()
                raise HardwareDecodeError(FallbackReason.STREAM_ERROR)
            reply: ChildReply = self._connection.recv()
        except (EOFError, OSError) as error:
            raise HardwareDecodeError(FallbackReason.STREAM_ERROR) from error
        return reply

    def _frame(self, image: DecodedImage) -> VideoFrame:
        frame = VideoFrame(image.width, image.height, I420_FORMAT)
        size = i420_bytes(image.width, image.height)
        source = np.ndarray((size,), np.uint8, self._memory.buf, image.slot * SLOT_BYTES)
        offset = 0
        for plane in frame.planes:
            plane_size = plane.width * plane.height
            rows = np.frombuffer(plane, np.uint8).reshape(-1, plane.line_size)[: plane.height, : plane.width]
            np.copyto(rows, source[offset : offset + plane_size].reshape(plane.height, plane.width))
            offset += plane_size
        frame.pts = image.pts
        cast(KeyFrameFlag, frame).key_frame = image.keyframe
        frame.color_range = image.color_range
        frame.colorspace = image.colorspace
        return frame

    def _stop_child(self) -> None:
        with contextlib.suppress(OSError):
            self._connection.send(None)
        self._process.join(STOP_TIMEOUT_SECONDS)
        if self._process.is_alive():
            self._process.kill()
            self._process.join(STOP_TIMEOUT_SECONDS)
