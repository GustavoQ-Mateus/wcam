import numpy as np

from wcam.virtualcam.sink import I420Frame

BLACK_LUMA = 16
NEUTRAL_CHROMA = 128


def black_i420(width: int, height: int) -> I420Frame:
    frame = np.full((height * 3 // 2, width), NEUTRAL_CHROMA, dtype=np.uint8)
    frame[:height] = BLACK_LUMA
    return frame
