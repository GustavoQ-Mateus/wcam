import time
from collections.abc import Callable

from aiortc.codecs import h264, vpx

MILLISECONDS_PER_SECOND = 1000
DECODER_CLASSES = (h264.H264Decoder, vpx.Vp8Decoder)
TIMED_MARK = "_wcam_timed"

type DecodeListener = Callable[[float], None]
type Decode = Callable[..., object]

listeners: list[DecodeListener] = []


def time_decoders(listener: DecodeListener) -> None:
    # aiortc decodes in its own thread with no hook; wrapping decode() is the only place to time it.
    listeners.append(listener)
    for decoder_class in DECODER_CLASSES:
        decode: Decode = decoder_class.decode
        if not getattr(decode, TIMED_MARK, False):
            decoder_class.decode = timed(decode)  # type: ignore[method-assign]


def timed(decode: Decode) -> Decode:
    def run(*arguments: object) -> object:
        started = time.perf_counter()
        try:
            return decode(*arguments)
        finally:
            elapsed = (time.perf_counter() - started) * MILLISECONDS_PER_SECOND
            for listener in listeners:
                listener(elapsed)

    setattr(run, TIMED_MARK, True)
    return run
