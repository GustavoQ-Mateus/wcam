from enum import Enum

import numpy as np
from numpy.typing import NDArray

class PixelFormat(Enum):
    I420 = "I420"

class Camera:
    def __init__(
        self,
        width: int,
        height: int,
        fps: float,
        *,
        fmt: PixelFormat = ...,
        backend: str | None = ...,
    ) -> None: ...
    def send(self, frame: NDArray[np.uint8]) -> None: ...
    def close(self) -> None: ...
