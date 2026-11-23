import heapq
import time
from collections import deque
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
    CloseStream,
    DecodedImage,
    DecodeFailed,
    EncodedPacket,
    OpenStream,
    PacketDecoded,
    StreamOpened,
    StreamPacket,
)
from wcam.decoding.status import FallbackReason
from wcam.process_priority import join_capture_task, raise_process_priority

HARDWARE_DEVICE = "dxva2"
COPIED_FORMAT = "nv12"
FAILURES_BEFORE_GIVING_UP = 10
MILLISECONDS_PER_SECOND = 1000
UNKNOWN_PTS = -1

type PendingPacket = tuple[int, int, bool]
type I420Target = np.ndarray[tuple[int], np.dtype[np.uint8]]


class PacketDecoder(Protocol):
    def decode(self, packet: object = None) -> list[VideoFrame]: ...


class SlotWriter(Protocol):
    @property
    def count(self) -> int: ...

    def write(self, frame: VideoFrame) -> int | None: ...


def i420_bytes(width: int, height: int) -> int:
    return width * height + 2 * ((width + 1) // 2) * ((height + 1) // 2)


def serve(connection: Connection, memory_name: str, slot_bytes: int, slot_count: int) -> None:
    raise_process_priority()
    join_capture_task()
    memory = SharedMemory(memory_name)
    try:
        ChildDecoder(connection, SharedSlots(memory, slot_bytes, slot_count)).run()
    finally:
        memory.close()


class SharedSlots:
    def __init__(self, memory: SharedMemory, slot_bytes: int, slot_count: int) -> None:
        self._memory = memory
        self._slot_bytes = slot_bytes
        self._slot_count = slot_count
        self._next_slot = 0

    @property
    def count(self) -> int:
        return self._slot_count

    def write(self, frame: VideoFrame) -> int | None:
        size = i420_bytes(frame.width, frame.height)
        if size > self._slot_bytes:
            return None
        slot = self._next_slot
        self._next_slot = (slot + 1) % self._slot_count
        write_i420(frame, np.ndarray((size,), np.uint8, self._memory.buf, slot * self._slot_bytes))
        return slot


class StreamDecoder:
    def __init__(self, context: VideoCodecContext, slots: SlotWriter) -> None:
        self._context = context
        self._slots = slots
        self._pending: list[PendingPacket] = []
        self._waiting: deque[VideoFrame] = deque()
        self._order = 0
        self._failures = 0
        self._decoded_any = False
        self._drained = False

    def decode(self, packet: EncodedPacket) -> PacketDecoded | DecodeFailed:
        if not packet.data:
            return self._drain()
        entry = (UNKNOWN_PTS if packet.pts is None else packet.pts, self._order, packet.keyframe)
        self._order += 1
        heapq.heappush(self._pending, entry)
        started = time.perf_counter()
        try:
            frames = cast(PacketDecoder, self._context).decode(Packet(packet.data))
        except FFmpegError:
            self._forget(entry)
            return self._failed()
        decode_milliseconds = elapsed_since(started)
        self._failures = 0
        self._waiting.extend(frames)
        return self._copied(decode_milliseconds)

    def _drain(self) -> PacketDecoded | DecodeFailed:
        started = time.perf_counter()
        if not self._drained:
            self._drained = True
            try:
                self._waiting.extend(cast(PacketDecoder, self._context).decode(None))
            except FFmpegError:
                return DecodeFailed(FallbackReason.STREAM_ERROR)
        return self._copied(elapsed_since(started))

    def _copied(self, decode_milliseconds: float) -> PacketDecoded | DecodeFailed:
        started = time.perf_counter()
        images: list[DecodedImage] = []
        while self._waiting and len(images) < self._slots.count:
            frame = self._waiting.popleft()
            if frame.format.name != COPIED_FORMAT:
                return DecodeFailed(FallbackReason.UNSUPPORTED)
            slot = self._slots.write(frame)
            if slot is None:
                return DecodeFailed(FallbackReason.UNSUPPORTED)
            images.append(self._image(slot, frame))
        self._decoded_any = self._decoded_any or bool(images)
        return PacketDecoded(tuple(images), decode_milliseconds, elapsed_since(started))

    def _image(self, slot: int, frame: VideoFrame) -> DecodedImage:
        pts, _, keyframe = heapq.heappop(self._pending) if self._pending else (UNKNOWN_PTS, 0, False)
        return DecodedImage(
            slot=slot,
            width=frame.width,
            height=frame.height,
            pts=None if pts == UNKNOWN_PTS else pts,
            keyframe=keyframe,
            color_range=int(self._context.color_range),
            colorspace=int(self._context.colorspace),
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


class ChildDecoder:
    def __init__(self, connection: Connection, slots: SlotWriter) -> None:
        self._connection = connection
        self._slots = slots
        self._streams: dict[int, StreamDecoder] = {}

    def run(self) -> None:
        while True:
            try:
                request: ChildRequest = self._connection.recv()
            except EOFError:
                return
            if request is None:
                return
            self._connection.send(self._answer(request))

    def _answer(self, request: OpenStream | CloseStream | StreamPacket) -> ChildReply:
        if isinstance(request, OpenStream):
            return self._open(request)
        if isinstance(request, CloseStream):
            self._streams.pop(request.stream_id, None)
            return None
        stream = self._streams.get(request.stream_id)
        if stream is None:
            return DecodeFailed(FallbackReason.STREAM_ERROR)
        return stream.decode(request.packet)

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
        self._streams[request.stream_id] = StreamDecoder(context, self._slots)
        return StreamOpened(None)


def write_i420(frame: VideoFrame, target: I420Target) -> None:
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
