"""
System telemetry dashboard for the 240×320 ILI9341 display.

Layout (portrait, 240×320):
    ┌──────────────────────────┐  y=0
    │         MU/TH/UR        │  header (28px)
    ├──────────────────────────┤  y=28
    │  CPU            25.4%   │  row (52px each × 5)
    ├──────────────────────────┤
    │  RAM            27.5%   │
    ├──────────────────────────┤
    │  DISK           20.7%   │
    ├──────────────────────────┤
    │  TEMP           45.2C   │
    ├──────────────────────────┤
    │  IP    10.64.32.100     │
    ├──────────────────────────┤  y=288
    │   2026-06-04  12:34:56  │  footer (32px)
    └──────────────────────────┘  y=320

Rendering strategy:
    Full-screen redraw every tick. At 240×320 and 16 MHz SPI this is
    under 100 ms and eliminates coordinate confusion with rotation=180.

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
_BG             = (  4,  12,   4)
_SURFACE        = (  7,  17,  10)
_BORDER         = ( 15,  34,  20)
_BORDER_BRIGHT  = ( 27,  66,  38)
_TEXT_PRIMARY   = (200, 224, 200)
_TEXT_SECONDARY = (106, 154, 106)
_TEXT_DIM       = ( 42,  74,  42)
_ACCENT         = (126, 198, 126)
_WARNING        = (232, 200,  74)
_ERROR          = (212,  80,  80)

# ---------------------------------------------------------------------------
# Layout constants (240×320 portrait)
# ---------------------------------------------------------------------------
_W, _H     = 240, 320
_HEADER_H  = 28
_FOOTER_H  = 32
_CONTENT_H = _H - _HEADER_H - _FOOTER_H   # 260
_ROW_COUNT = 5
_ROW_H     = _CONTENT_H // _ROW_COUNT      # 52

_PAD         = 8
_LABEL_X     = _PAD
_VALUE_RIGHT = _W - _PAD

# ---------------------------------------------------------------------------
# Font loading
# Preference: user-supplied TTF → system monospace → Pillow built-in
# ---------------------------------------------------------------------------
_FONT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")
)

_SYSTEM_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
]

_USER_FONTS = ["IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf", "CityLight.ttf"]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in _USER_FONTS:
        path = os.path.join(_FONT_DIR, name)
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    for path in _SYSTEM_FONTS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


_FONT_HEADER = _load_font(15)
_FONT_LABEL  = _load_font(14)
_FONT_VALUE  = _load_font(20)
_FONT_FOOTER = _load_font(11)

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------
_image:  Image.Image | None = None
_draw:   ImageDraw.ImageDraw | None = None
_display = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init(display: "ili9341_type.ILI9341") -> None:
    """Render the first frame and push it to the display."""
    global _image, _draw, _display
    _display = display
    _image   = Image.new("RGB", (_W, _H), _BG)
    _draw    = ImageDraw.Draw(_image)
    _render()
    display.image(_image)


def update() -> None:
    """Redraw with fresh telemetry and push the full frame."""
    if _image is None or _display is None:
        return
    _render()
    _display.image(_image)


# ---------------------------------------------------------------------------
# Internal rendering
# ---------------------------------------------------------------------------

def _render() -> None:
    d = _draw

    # Clear canvas
    d.rectangle([(0, 0), (_W - 1, _H - 1)], fill=_BG)

    # Header
    d.rectangle([(0, 0), (_W - 1, _HEADER_H - 1)], fill=_SURFACE)
    d.line([(0, _HEADER_H - 1), (_W - 1, _HEADER_H - 1)], fill=_BORDER_BRIGHT, width=1)
    _draw_centered(d, "MU/TH/UR", 0, _HEADER_H, _FONT_HEADER, _ACCENT)

    # Telemetry rows
    temp_val = cpu_temp()
    rows = [
        ("CPU",  f"{cpu_percent():.1f}%",                               "cpu"),
        ("RAM",  f"{ram_percent():.1f}%",                               "ram"),
        ("DISK", f"{disk_percent():.1f}%",                              "disk"),
        ("TEMP", f"{temp_val:.1f}C" if temp_val is not None else "N/A", "temp"),
        ("IP",   ip_address(),                                          "ip"),
    ]

    for i, (label, value, key) in enumerate(rows):
        row_y  = _HEADER_H + i * _ROW_H
        row_y2 = row_y + _ROW_H

        # Alternate row background
        if i % 2 == 1:
            d.rectangle([(0, row_y), (_W - 1, row_y2 - 1)], fill=_SURFACE)

        # Row separator
        d.line([(0, row_y2 - 1), (_W - 1, row_y2 - 1)], fill=_BORDER, width=1)

        # Label — left edge, vertically centred
        lbbox = d.textbbox((0, 0), label, font=_FONT_LABEL)
        lh    = lbbox[3] - lbbox[1]
        ly    = row_y + (_ROW_H - lh) // 2
        d.text((_LABEL_X, ly), label, font=_FONT_LABEL, fill=_TEXT_SECONDARY)

        # Value — right-aligned, vertically centred
        vbbox = d.textbbox((0, 0), value, font=_FONT_VALUE)
        vw    = vbbox[2] - vbbox[0]
        vh    = vbbox[3] - vbbox[1]
        vx    = _VALUE_RIGHT - vw
        vy    = row_y + (_ROW_H - vh) // 2
        d.text((vx, vy), value, font=_FONT_VALUE, fill=_value_color(key, value))

    # Footer
    footer_y = _HEADER_H + _ROW_COUNT * _ROW_H
    d.rectangle([(0, footer_y), (_W - 1, _H - 1)], fill=_SURFACE)
    d.line([(0, footer_y), (_W - 1, footer_y)], fill=_BORDER, width=1)
    time_str = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    _draw_centered(d, time_str, footer_y, _H, _FONT_FOOTER, _TEXT_DIM)


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
