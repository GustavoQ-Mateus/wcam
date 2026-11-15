from PIL import Image, ImageDraw

from wcam.tray.menu import TrayState

ICON_SIZE = 64
MARGIN = 8
RING_WIDTH = 8
BAR_WIDTH = 14
BAR_GAP = 10
DATA = "#3ecf8e"
DATA_2 = "#e6e6e6"
WARNING = "#e5a93b"
MUTED = "#b4b4b4"
NEGATIVE = "#e5484d"
TRANSPARENT = (0, 0, 0, 0)


def tray_icon(state: TrayState) -> Image.Image:
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    low, high = MARGIN, ICON_SIZE - MARGIN
    if state is TrayState.LIVE:
        draw.ellipse((low, low, high, high), fill=DATA)
    elif state is TrayState.FROZEN:
        draw.rectangle((low, low, high, high), fill=DATA_2)
    elif state is TrayState.CAMERA_OFF:
        draw_bars(draw, low, high)
    elif state is TrayState.WAITING:
        draw.ellipse((low, low, high, high), outline=MUTED, width=RING_WIDTH)
    else:
        draw.polygon(((ICON_SIZE / 2, low), (high, high), (low, high)), fill=NEGATIVE)
    return image


def draw_bars(draw: ImageDraw.ImageDraw, low: int, high: int) -> None:
    left = (ICON_SIZE - 2 * BAR_WIDTH - BAR_GAP) // 2
    right = left + BAR_WIDTH + BAR_GAP
    draw.rectangle((left, low, left + BAR_WIDTH, high), fill=WARNING)
    draw.rectangle((right, low, right + BAR_WIDTH, high), fill=WARNING)
