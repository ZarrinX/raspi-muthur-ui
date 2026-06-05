"""
System telemetry dashboard for the 240×320 ILI9341 display.

Layout (portrait, 240×320):
    ┌──────────────────────────┐  y=0
    │  MU/TH/UR   [header]    │  y=32
    ├──────────────────────────┤
    │  CPU    │  XX.X%        │  y=52
    │  ────────────────────── │
    │  RAM    │  XX.X%        │  y=96
    │  ────────────────────── │
    │  DISK   │  XX.X%        │  y=140
    │  ────────────────────── │
    │  TEMP   │  XX.X°C       │  y=184
    │  ────────────────────── │
    │  IP  XXX.XXX.XXX.XXX   │  y=240
    │  ────────────────────── │
    ├──────────────────────────┤  y=298
    │  YYYY-MM-DD  HH:MM:SS   │  y=320
    └──────────────────────────┘

Rendering strategy:
    - init()   draws the full static layout once and pushes the whole frame.
    - update() reads fresh telemetry, repaints only the value bounding boxes,
               and pushes those sub-images — no full-screen redraws.

Palette sourced from muthur-ui/packages/ui/src/styles/global.css.
"""

from __future__ import annotations

import datetime
import os
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

from utils.telemetry import cpu_percent, cpu_temp, disk_percent, ip_address, ram_percent

if TYPE_CHECKING:
    import adafruit_rgb_display.ili9341 as ili9341_type

# ---------------------------------------------------------------------------
# Palette — muthur-ui/packages/ui/src/styles/global.css
# ---------------------------------------------------------------------------
_BG              = (  4,  12,   4)   # --color-bg
_SURFACE         = (  7,  17,  10)   # --color-surface
_BORDER          = ( 15,  34,  20)   # --color-border
_BORDER_BRIGHT   = ( 27,  66,  38)   # --color-border-bright
_TEXT_PRIMARY    = (200, 224, 200)   # --color-text-primary
_TEXT_SECONDARY  = (106, 154, 106)   # --color-text-secondary
_TEXT_DIM        = ( 42,  74,  42)   # --color-text-dim
_ACCENT          = (126, 198, 126)   # --color-accent
_WARNING         = (232, 200,  74)   # --color-warning
_ERROR           = (212,  80,  80)   # --color-error

# ---------------------------------------------------------------------------
# Layout constants (240×320 portrait)
# ---------------------------------------------------------------------------
_W, _H        = 240, 320
_HEADER_H     = 32
_FOOTER_H     = 22
_PAD          = 8
_DIVIDER_X    = 82   # x position of the label/value vertical divider
_VALUE_X      = _DIVIDER_X + 6
_VALUE_RIGHT  = _W - _PAD

_HEADER_Y1    = 0
_HEADER_Y2    = _HEADER_H
_FOOTER_Y1    = _H - _FOOTER_H
_FOOTER_Y2    = _H

# Row definitions: (label_text, region_key, label_y)
_ROW_H = 44
_ROWS: list[tuple[str, str, int]] = [
    ("CPU",  "cpu",  _HEADER_H + 10),
    ("RAM",  "ram",  _HEADER_H + 10 + _ROW_H),
    ("DISK", "disk", _HEADER_H + 10 + _ROW_H * 2),
    ("TEMP", "temp", _HEADER_H + 10 + _ROW_H * 3),
    ("IP",   "ip",   _HEADER_H + 10 + _ROW_H * 4 + 8),
]

# Value bounding boxes: {key: (x1, y1, x2, y2)}
_VALUE_REGIONS: dict[str, tuple[int, int, int, int]] = {
    key: (_VALUE_X, y + 2, _VALUE_RIGHT, y + _ROW_H - 8)
    for _, key, y in _ROWS
}
_VALUE_REGIONS["time"] = (
    _PAD + 2,
    _FOOTER_Y1 + 4,
    _W - _PAD - 2,
    _FOOTER_Y2 - 4,
)

# ---------------------------------------------------------------------------
# Font loading
# Preference: City Light → IBM Plex Mono (place TTFs in assets/fonts/)
# Fallback: PIL default bitmap font (very small but always available)
# ---------------------------------------------------------------------------
_FONT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "CityLight.ttf"):
        path = os.path.join(_FONT_DIR, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


_FONT_HEADER = _load_font(14)
_FONT_LABEL  = _load_font(12)
_FONT_VALUE  = _load_font(15)
_FONT_FOOTER = _load_font(10)

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------
_image:   Image.Image | None = None
_draw:    ImageDraw.ImageDraw | None = None
_display = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init(display: "ili9341_type.ILI9341") -> None:
    """Draw the static layout once and push the full frame to the display."""
    global _image, _draw, _display
    _display = display
    _image   = Image.new("RGB", (_W, _H), _BG)
    _draw    = ImageDraw.Draw(_image)
    _draw_static()
    display.image(_image)


def update() -> None:
    """Collect fresh telemetry and repaint only the value regions."""
    if _image is None or _display is None:
        return

    temp = cpu_temp()
    data: dict[str, str] = {
        "cpu":  f"{cpu_percent():5.1f}%",
        "ram":  f"{ram_percent():5.1f}%",
        "disk": f"{disk_percent():5.1f}%",
        "temp": f"{temp:5.1f}C" if temp is not None else "  N/A",
        "ip":   ip_address(),
        "time": datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S"),
    }

    for key, text in data.items():
        _repaint_value(key, text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _draw_static() -> None:
    d = _draw

    # Header bar
    d.rectangle([(0, _HEADER_Y1), (_W - 1, _HEADER_Y2)], fill=_SURFACE)
    d.rectangle([(0, _HEADER_Y1), (_W - 1, _HEADER_Y2)], outline=_BORDER_BRIGHT)
    _draw_centered(d, "MU/TH/UR", _HEADER_Y1, _HEADER_Y2, _FONT_HEADER, _ACCENT)

    # Footer bar
    d.rectangle([(0, _FOOTER_Y1), (_W - 1, _FOOTER_Y2)], fill=_SURFACE)
    d.rectangle([(0, _FOOTER_Y1), (_W - 1, _FOOTER_Y2)], outline=_BORDER)

    # Content border
    d.rectangle(
        [(_PAD, _HEADER_Y2 + 2), (_W - _PAD - 1, _FOOTER_Y1 - 2)],
        outline=_BORDER,
    )

    # Vertical divider between label and value columns
    d.line(
        [(_DIVIDER_X, _HEADER_Y2 + 6), (_DIVIDER_X, _FOOTER_Y1 - 6)],
        fill=_BORDER,
        width=1,
    )

    # Row labels and horizontal separators
    for label, _, y in _ROWS:
        d.text((_PAD + 4, y + 4), label, font=_FONT_LABEL, fill=_TEXT_SECONDARY)
        # separator below each row
        sep_y = y + _ROW_H - 4
        d.line([(_PAD + 2, sep_y), (_W - _PAD - 2, sep_y)], fill=_BORDER, width=1)


def _repaint_value(key: str, text: str) -> None:
    """Erase a value region, redraw the text, push the sub-image."""
    x1, y1, x2, y2 = _VALUE_REGIONS[key]

    # Erase
    _draw.rectangle([(x1, y1), (x2, y2)], fill=_BG)

    # Draw
    color = _value_color(key, text)
    font  = _FONT_FOOTER if key == "time" else _FONT_VALUE
    _draw.text((x1 + 2, y1 + 1), text.strip(), font=font, fill=color)

    # Partial push — only this sub-image
    region_img = _image.crop((x1, y1, x2 + 1, y2 + 1))
    _display.image(region_img, x=x1, y=y1)


def _draw_centered(
    d: ImageDraw.ImageDraw,
    text: str,
    y1: int,
    y2: int,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    color: tuple[int, int, int],
) -> None:
    bbox = d.textbbox((0, 0), text, font=font)
    tw   = bbox[2] - bbox[0]
    th   = bbox[3] - bbox[1]
    x    = (_W - tw) // 2
    y    = y1 + (y2 - y1 - th) // 2
    d.text((x, y), text, font=font, fill=color)


def _value_color(key: str, text: str) -> tuple[int, int, int]:
    if key == "time":
        return _TEXT_DIM

    val = _parse_float(text)

    if key in ("cpu", "ram", "disk") and val is not None:
        if val >= 90:
            return _ERROR
        if val >= 75:
            return _WARNING

    if key == "temp" and val is not None:
        if val >= 80:
            return _ERROR
        if val >= 65:
            return _WARNING

    return _TEXT_PRIMARY


def _parse_float(text: str) -> float | None:
    try:
        return float(text.strip().rstrip("%C"))
    except ValueError:
        return None
