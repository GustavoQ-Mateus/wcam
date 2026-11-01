import sys
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

WIDTH = 1920
HEIGHT = 1080
SEED = 20261101
GLYPH_WIDTH = 3
GLYPH_HEIGHT = 5
GLYPH_COUNT = 64
TEXT_LINE_SPACING = 3
TEXT_COLUMN_SPACING = 1
NOISE_AMPLITUDE = 12
HEADER = f"YUV4MPEG2 W{WIDTH} H{HEIGHT} F30:1 Ip A1:1 C420jpeg\n".encode()
FRAME_MARKER = b"FRAME\n"
EXIT_USAGE = 2

type Plane = NDArray[np.uint8]


def reference_frame() -> bytes:
    generator = np.random.default_rng(SEED)
    luma = reference_luma(generator)
    blue, red = reference_chroma()
    return HEADER + FRAME_MARKER + luma.tobytes() + blue.tobytes() + red.tobytes()


def reference_luma(generator: np.random.Generator) -> Plane:
    columns = np.arange(WIDTH)
    rows = np.arange(HEIGHT)
    luma = np.tile(16 + columns * 219 // (WIDTH - 1), (HEIGHT, 1)).astype(np.int32)
    quarter = WIDTH // 4
    third = HEIGHT // 3
    luma[:third, :quarter] = np.where(columns[:quarter] % 2 == 0, 235, 16)
    luma[:third, quarter : 2 * quarter] = np.where(rows[:third, None] % 2 == 0, 235, 16)
    luma[third : 2 * third, :] = draw_text(generator, (third, WIDTH))
    noise = generator.integers(-NOISE_AMPLITUDE, NOISE_AMPLITUDE + 1, size=(HEIGHT - 2 * third, WIDTH))
    luma[2 * third :, :] = np.clip(luma[2 * third :, :] + noise, 16, 235)
    return luma.astype(np.uint8)


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


def reference_chroma() -> tuple[Plane, Plane]:
    rows = np.arange(HEIGHT // 2)[:, None]
    columns = np.arange(WIDTH // 2)[None, :]
    blue = 16 + (columns * 224 // (WIDTH // 2 - 1)) + rows * 0
    red = 16 + (rows * 224 // (HEIGHT // 2 - 1)) + columns * 0
    return blue.astype(np.uint8), red.astype(np.uint8)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python -m wcam.tools.make_reference <output.y4m>", file=sys.stderr)
        sys.exit(EXIT_USAGE)
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(reference_frame())


if __name__ == "__main__":
    main()
