import numpy as np

from wcam.virtualcam.sink import I420Frame, Nv12Frame, frame_size


def i420_planes(frame: I420Frame, width: int, height: int) -> tuple[I420Frame, I420Frame, I420Frame]:
    flat = frame.reshape(-1)
    luma_size = width * height
    chroma_size = luma_size // 4
    luma = flat[:luma_size].reshape(height, width)
    blue = flat[luma_size : luma_size + chroma_size].reshape(height // 2, width // 2)
    red = flat[luma_size + chroma_size : luma_size + 2 * chroma_size].reshape(height // 2, width // 2)
    return luma, blue, red


def nv12_from_i420(frame: I420Frame) -> Nv12Frame:
    width, height = frame_size(frame)
    luma, blue, red = i420_planes(frame, width, height)
    nv12 = np.empty_like(frame)
    nv12[:height] = luma
    chroma = nv12[height:].reshape(height // 2, width // 2, 2)
    chroma[:, :, 0] = blue
    chroma[:, :, 1] = red
    return nv12
