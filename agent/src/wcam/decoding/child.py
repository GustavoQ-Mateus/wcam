import heapq
import time
from multiprocessing.connection import Connection
from multiprocessing.shared_memory import SharedMemory
from typing import Protocol, cast

import av
import numpy as np
from av import Packet, VideoFrame
from av.codec.hwaccel import HWAccel
from av.error import FFmpegError
from av.video.codeccontext import VideoCodecContext
from av.video.plane import VideoPlane

from wcam.decoding.messages import (
    ChildReply,
    ChildRequest,
    DecodedImage,
    DecodeFailed,
    EncodedPacket,
    OpenStream,
    PacketDecoded,
    StreamOpened,
)
from wcam.decoding.status import FallbackReason

HARDWARE_DEVICE = "dxva2"
COPIED_FORMAT = "nv12"
FAILURES_BEFORE_GIVING_UP = 10
MILLISECONDS_PER_SECOND = 1000
UNKNOWN_PTS = -1

type PendingPacket = tuple[int, int, bool]


class PacketDecoder(Protocol):
    def decode(self, packet: object) -> list[VideoFrame]: ...


def i420_bytes(width: int, height: int) -> int:
    return width * height + 2 * ((width + 1) // 2) * ((height + 1) // 2)


def serve(connection: Connection, memory_name: str, slot_bytes: int, slot_count: int) -> None:
    memory = SharedMemory(memory_name)
    try:
        ChildDecoder(connection, memory, slot_bytes, slot_count).run()
    finally:
        memory.close()


class ChildDecoder:
    def __init__(self, connection: Connection, memory: SharedMemory, slot_bytes: int, slot_count: int) -> None:
        self._connection = connection
        self._memory = memory
        self._slot_bytes = slot_bytes
        self._slot_count = slot_count
        self._next_slot = 0
        self._context: VideoCodecContext | None = None
        self._pending: list[PendingPacket] = []
        self._order = 0
        self._failures = 0
        self._decoded_any = False

    def run(self) -> None:
        while True:
            try:
                request: ChildRequest = self._connection.recv()
            except EOFError:
                return
            if request is None:
                return
            self._connection.send(self._answer(request))

    def _answer(self, request: OpenStream | EncodedPacket) -> ChildReply:
        if isinstance(request, OpenStream):
            return self._open(request)
        return self._decode(request)

    def _open(self, request: OpenStream) -> StreamOpened:
        try:
            context = av.CodecContext.create(
                request.codec, "r", hwaccel=HWAccel(HARDWARE_DEVICE, allow_software_fallback=False)
            )
        except FFmpegError:
            return StreamOpened(FallbackReason.OPEN_FAILED)
        if not isinstance(context, VideoCodecContext) or not context.is_hwaccel:
            return StreamOpened(FallbackReason.UNSUPPORTED)
        if request.extradata:
            context.extradata = request.extradata
        self._context = context
        self._pending = []
        self._failures = 0
        self._decoded_any = False
        return StreamOpened(None)

    def _decode(self, request: EncodedPacket) -> PacketDecoded | DecodeFailed:
        context = self._context
        if context is None:
            return DecodeFailed(FallbackReason.OPEN_FAILED)
        entry = (UNKNOWN_PTS if request.pts is None else request.pts, self._order, request.keyframe)
        self._order += 1
        heapq.heappush(self._pending, entry)
        started = time.perf_counter()
        try:
            frames = cast(PacketDecoder, context).decode(Packet(request.data))
        except FFmpegError:
            self._forget(entry)
            return self._failed()
        decode_milliseconds = elapsed_since(started)
        self._failures = 0
        return self._copied(frames, context, decode_milliseconds)

    def _copied(
        self, frames: list[VideoFrame], context: VideoCodecContext, decode_milliseconds: float
    ) -> PacketDecoded | DecodeFailed:
        started = time.perf_counter()
        images: list[DecodedImage] = []
        for frame in frames[: self._slot_count]:
            if frame.format.name != COPIED_FORMAT or i420_bytes(frame.width, frame.height) > self._slot_bytes:
                return DecodeFailed(FallbackReason.UNSUPPORTED)
            images.append(self._written(frame, context))
        self._decoded_any = self._decoded_any or bool(images)
        return PacketDecoded(tuple(images), decode_milliseconds, elapsed_since(started))

    def _written(self, frame: VideoFrame, context: VideoCodecContext) -> DecodedImage:
        slot = self._next_slot
        self._next_slot = (slot + 1) % self._slot_count
        offset = slot * self._slot_bytes
        target = np.ndarray((i420_bytes(frame.width, frame.height),), np.uint8, self._memory.buf, offset)
        write_i420(frame, target)
        pts, _, keyframe = heapq.heappop(self._pending) if self._pending else (UNKNOWN_PTS, 0, False)
        return DecodedImage(
            slot=slot,
            width=frame.width,
            height=frame.height,
            pts=None if pts == UNKNOWN_PTS else pts,
            keyframe=keyframe,
            color_range=int(context.color_range),
            colorspace=int(context.colorspace),
        )

    def _forget(self, entry: PendingPacket) -> None:
        if entry in self._pending:
            self._pending.remove(entry)
            heapq.heapify(self._pending)

    def _failed(self) -> PacketDecoded | DecodeFailed:
        self._failures += 1
        if self._failures < FAILURES_BEFORE_GIVING_UP:
            return PacketDecoded((), 0.0, 0.0)
        reason = FallbackReason.STREAM_ERROR if self._decoded_any else FallbackReason.UNSUPPORTED
        return DecodeFailed(reason)


def write_i420(frame: VideoFrame, target: np.ndarray[tuple[int], np.dtype[np.uint8]]) -> None:
    luma_plane, chroma_plane = frame.planes
    width, height = frame.width, frame.height
    chroma_width, chroma_height = (width + 1) // 2, (height + 1) // 2
    luma_size = width * height
    chroma_size = chroma_width * chroma_height
    chroma = plane_rows(chroma_plane, chroma_height, 2 * chroma_width)
    np.copyto(target[:luma_size].reshape(height, width), plane_rows(luma_plane, height, width))
    np.copyto(target[luma_size : luma_size + chroma_size].reshape(chroma_height, chroma_width), chroma[:, 0::2])
    np.copyto(target[luma_size + chroma_size :].reshape(chroma_height, chroma_width), chroma[:, 1::2])


def plane_rows(plane: VideoPlane, height: int, width: int) -> np.ndarray[tuple[int, int], np.dtype[np.uint8]]:
    rows = np.frombuffer(plane, np.uint8).reshape(-1, plane.line_size)
    return rows[:height, :width]


def elapsed_since(started: float) -> float:
    return (time.perf_counter() - started) * MILLISECONDS_PER_SECOND
