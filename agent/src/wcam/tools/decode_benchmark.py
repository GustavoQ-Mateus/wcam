import time
from dataclasses import dataclass

import psutil

from wcam.media.quality_preset import QualityPreset
from wcam.tools.synthetic_h264 import decode, encode, h264_decoder, h264_encoder, moving_frames

FORMATS = ((1280, 720), (1920, 1080), (2560, 1440), (3840, 2160))
FRAME_RATES = (30, 60)
VIDEO_SECONDS = 2
BITRATE_BPS = QualityPreset.MAXIMUM.max_bitrate_bps
PERCENT = 100
MILLISECONDS_PER_SECOND = 1000
TABLE_HEADER = (
    "| Format | fps | Frames | Decode ms/frame | CPU of one core | CPU of the machine |\n|---|---|---|---|---|---|"
)


@dataclass(frozen=True, slots=True)
class DecodeResult:
    width: int
    height: int
    fps: int
    frames: int
    milliseconds_per_frame: float
    percent_of_one_core: float
    percent_of_machine: float


def measure(width: int, height: int, fps: int, video_seconds: float = VIDEO_SECONDS) -> DecodeResult:
    frame_count = round(fps * video_seconds)
    packets = encode(moving_frames(width, height, frame_count), h264_encoder(width, height, fps, BITRATE_BPS))
    decoder = h264_decoder()
    process = psutil.Process()
    cpu_before = process_cpu_seconds(process)
    started = time.perf_counter()
    frames = decode(packets, decoder)
    elapsed = time.perf_counter() - started
    cpu_seconds = process_cpu_seconds(process) - cpu_before
    percent_of_one_core = cpu_seconds / (len(frames) / fps) * PERCENT
    return DecodeResult(
        width=width,
        height=height,
        fps=fps,
        frames=len(frames),
        milliseconds_per_frame=elapsed / len(frames) * MILLISECONDS_PER_SECOND,
        percent_of_one_core=percent_of_one_core,
        percent_of_machine=percent_of_one_core / (psutil.cpu_count() or 1),
    )


def process_cpu_seconds(process: psutil.Process) -> float:
    times = process.cpu_times()
    return times.user + times.system


def table_row(result: DecodeResult) -> str:
    return (
        f"| {result.width}x{result.height} | {result.fps} | {result.frames} | "
        f"{result.milliseconds_per_frame:.1f} | {result.percent_of_one_core:.0f}% | {result.percent_of_machine:.1f}% |"
    )


def main() -> None:
    print(f"H.264 at {BITRATE_BPS // 1_000_000} Mbit/s, {VIDEO_SECONDS} s per format, {psutil.cpu_count()} cores")
    print(TABLE_HEADER)
    for width, height in FORMATS:
        for fps in FRAME_RATES:
            print(table_row(measure(width, height, fps)), flush=True)


if __name__ == "__main__":
    main()
