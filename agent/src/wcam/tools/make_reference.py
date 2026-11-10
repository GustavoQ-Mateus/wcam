import argparse
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

WIDTH = 1920
HEIGHT = 1080
FPS = 30
SEED = 20261101
GLYPH_WIDTH = 3
GLYPH_HEIGHT = 5
GLYPH_COUNT = 64
TEXT_LINE_SPACING = 3
TEXT_COLUMN_SPACING = 1
THREAD_PIXELS = 3
TWILL_REPEAT = 4
TEXTURE_CONTRAST = 40
CONTRAST_FLOOR = 0.6
CONTRAST_SWING = 0.4
FRAME_MARKER = b"FRAME\n"

type Plane = NDArray[np.uint8]


def y4m_header(width: int, height: int, fps: int) -> bytes:
    return f"YUV4MPEG2 W{width} H{height} F{fps}:1 Ip A1:1 C420jpeg\n".encode()


def reference_frame(width: int = WIDTH, height: int = HEIGHT, fps: int = FPS) -> bytes:
    if width % 2 or height % 2:
        raise ValueError("width and height must be even")
    generator = np.random.default_rng(SEED)
    luma = reference_luma(generator, width, height)
    blue, red = reference_chroma(width, height)
    return y4m_header(width, height, fps) + FRAME_MARKER + luma.tobytes() + blue.tobytes() + red.tobytes()


def reference_luma(generator: np.random.Generator, width: int, height: int) -> Plane:
    columns = np.arange(width)
    rows = np.arange(height)
    luma = np.tile(16 + columns * 219 // (width - 1), (height, 1)).astype(np.int32)
    quarter = width // 4
    third = height // 3
    luma[:third, :quarter] = np.where(columns[:quarter] % 2 == 0, 235, 16)
    luma[:third, quarter : 2 * quarter] = np.where(rows[:third, None] % 2 == 0, 235, 16)
    luma[third : 2 * third, :] = draw_text(generator, (third, width))
    luma[2 * third :, :] = np.clip(luma[2 * third :, :] + weave((height - 2 * third, width)), 16, 235)
    return luma.astype(np.uint8)


def weave(shape: tuple[int, int]) -> NDArray[np.int32]:
    rows = np.arange(shape[0])[:, None]
    columns = np.arange(shape[1])[None, :]
    warp_on_top = (columns // THREAD_PIXELS - rows // THREAD_PIXELS) % TWILL_REPEAT < TWILL_REPEAT // 2
    warp_shading = np.sin(np.pi * (columns % THREAD_PIXELS + 0.5) / THREAD_PIXELS)
    weft_shading = np.sin(np.pi * (rows % THREAD_PIXELS + 0.5) / THREAD_PIXELS)
    contrast = CONTRAST_FLOOR + CONTRAST_SWING * np.sin(2 * np.pi * columns / shape[1]) * np.cos(
        np.pi * rows / shape[0]
    )
    relief = np.where(warp_on_top, warp_shading, -weft_shading)
    return np.round(TEXTURE_CONTRAST * contrast * relief).astype(np.int32)


def draw_text(generator: np.random.Generator, shape: tuple[int, int]) -> NDArray[np.int32]:
    glyphs = generator.integers(0, 2, size=(GLYPH_COUNT, GLYPH_HEIGHT, GLYPH_WIDTH)).astype(np.int32)
    cell_height = GLYPH_HEIGHT + TEXT_LINE_SPACING
    cell_width = GLYPH_WIDTH + TEXT_COLUMN_SPACING
    lines = shape[0] // cell_height
    characters = shape[1] // cell_width
    picks = generator.integers(0, GLYPH_COUNT, size=(lines, characters))
    cells = np.zeros((lines, characters, cell_height, cell_width), dtype=np.int32)
    cells[:, :, :GLYPH_HEIGHT, :GLYPH_WIDTH] = glyphs[picks]
    ink = cells.transpose(0, 2, 1, 3).reshape(lines * cell_height, characters * cell_width)
    page = np.full(shape, 235, dtype=np.int32)
    page[: ink.shape[0], : ink.shape[1]] = np.where(ink == 1, 16, 235)
    return page


def reference_chroma(width: int, height: int) -> tuple[Plane, Plane]:
    rows = np.arange(height // 2)[:, None]
    columns = np.arange(width // 2)[None, :]
    blue = 16 + (columns * 224 // (width // 2 - 1)) + rows * 0
    red = 16 + (rows * 224 // (height // 2 - 1)) + columns * 0
    return blue.astype(np.uint8), red.astype(np.uint8)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m wcam.tools.make_reference")
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, default=WIDTH)
    parser.add_argument("--height", type=int, default=HEIGHT)
    parser.add_argument("--fps", type=int, default=FPS)
    arguments = parser.parse_args()
    output: Path = arguments.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(reference_frame(arguments.width, arguments.height, arguments.fps))


if __name__ == "__main__":
    main()
