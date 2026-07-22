"""
Network info page for the 240×320 ILI9341 display.

Layout (portrait, 240×320):
    ┌──────────────────────────┐  y=0
    │  NETWORK           2/2  │  header (28px)
    ├──────────────────────────┤  y=28
    │  HOST   tars             │  row (52px each × 5)
    ├──────────────────────────┤
    │  RX     1.23 GB          │
    ├──────────────────────────┤
    │  TX     456.7 MB         │
    ├──────────────────────────┤
    │  SSH    2                │
    ├──────────────────────────┤
    │  TOP    python3          │
    ├──────────────────────────┤  y=288
    │   2026-07-22  12:34:56  │  footer (32px)
    └──────────────────────────┘  y=320
"""

from __future__ import annotations

import datetime
import os
import socket
from typing import TYPE_CHECKING

import psutil
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    import adafruit_rgb_display.ili9341 as ili9341_type

# ---------------------------------------------------------------------------
# Palette — shared with system.py
# ---------------------------------------------------------------------------
_BG             = (  4,   8,  18)
_SURFACE        = (  7,  14,  30)
_BORDER         = ( 15,  30,  60)
_BORDER_BRIGHT  = ( 27,  60, 120)
_TEXT_PRIMARY   = (200, 215, 240)
_TEXT_SECONDARY = ( 90, 140, 210)
_TEXT_DIM       = ( 36,  60, 100)
_ACCENT         = ( 80, 160, 255)

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
# Font loading (mirrors system.py)
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


_FONT_HEADER = _load_font(20)
_FONT_LABEL  = _load_font(14)
_FONT_VALUE  = _load_font(20)
_FONT_FOOTER = _load_font(11)

# ---------------------------------------------------------------------------
# Module state
# ---------------------------------------------------------------------------
_image:   Image.Image | None = None
_draw:    ImageDraw.ImageDraw | None = None
_display  = None


# ---------------------------------------------------------------------------
# Telemetry helpers
# ---------------------------------------------------------------------------

def _hostname() -> str:
    return socket.gethostname()


def _format_bytes(b: int) -> str:
    """Format a byte count as a human-readable string."""
    if b >= 1_073_741_824:
        return f"{b / 1_073_741_824:.2f} GB"
    if b >= 1_048_576:
        return f"{b / 1_048_576:.1f} MB"
    if b >= 1024:
        return f"{b / 1024:.0f} KB"
    return f"{b} B"


def _net_bytes() -> tuple[int, int]:
    """Return (bytes_recv, bytes_sent) cumulative since boot."""
    counters = psutil.net_io_counters()
    if counters is None:
        return 0, 0
    return counters.bytes_recv, counters.bytes_sent


def _ssh_sessions() -> int:
    """Count established inbound SSH connections (local port 22)."""
    try:
        return sum(
            1
            for c in psutil.net_connections(kind="tcp")
            if c.laddr.port == 22 and c.status == psutil.CONN_ESTABLISHED
        )
    except (psutil.AccessDenied, AttributeError):
        return -1  # permission denied — show as unknown


def _top_process() -> str:
    """Return the name of the process with the highest CPU usage."""
    try:
        procs = [
            p.info
            for p in psutil.process_iter(["name", "cpu_percent"])
            if p.info["cpu_percent"] is not None
        ]
        if not procs:
            return "N/A"
        top = max(procs, key=lambda p: p["cpu_percent"])
        name = top["name"] or "?"
        # Truncate to fit the value column
        return name[:14]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return "N/A"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init(display: "ili9341_type.ILI9341", page_info: tuple[int, int] = (1, 1)) -> None:
    """Render the first frame and push it to the display."""
    global _image, _draw, _display
    _display = display
    _image   = Image.new("RGB", (_W, _H), _BG)
    _draw    = ImageDraw.Draw(_image)
    _render(page_info)
    display.image(_image)


def update(page_info: tuple[int, int] = (1, 1)) -> None:
    """Redraw with fresh telemetry and push the full frame."""
    if _image is None or _display is None:
        return
    _render(page_info)
    _display.image(_image)


# ---------------------------------------------------------------------------
# Internal rendering
# ---------------------------------------------------------------------------

def _render(page_info: tuple[int, int]) -> None:
    d = _draw

    # Clear canvas
    d.rectangle([(0, 0), (_W - 1, _H - 1)], fill=_BG)

    # Header
    d.rectangle([(0, 0), (_W - 1, _HEADER_H - 1)], fill=_SURFACE)
    d.line([(0, _HEADER_H - 1), (_W - 1, _HEADER_H - 1)], fill=_BORDER_BRIGHT, width=1)
    _draw_centered(d, "NETWORK", 0, _HEADER_H, _FONT_HEADER, _ACCENT)

    # Page indicator (right-aligned in header)
    page_str = f"{page_info[0]}/{page_info[1]}"
    pbbox = d.textbbox((0, 0), page_str, font=_FONT_FOOTER)
    px = _W - _PAD - (pbbox[2] - pbbox[0])
    py = (_HEADER_H - (pbbox[3] - pbbox[1])) // 2
    d.text((px, py), page_str, font=_FONT_FOOTER, fill=_TEXT_DIM)

    # Telemetry rows
    rx_b, tx_b  = _net_bytes()
    ssh_count   = _ssh_sessions()
    ssh_str     = str(ssh_count) if ssh_count >= 0 else "?"

    rows = [
        ("HOST", _hostname()),
        ("RX",   _format_bytes(rx_b)),
        ("TX",   _format_bytes(tx_b)),
        ("SSH",  ssh_str),
        ("TOP",  _top_process()),
    ]

    for i, (label, value) in enumerate(rows):
        row_y  = _HEADER_H + i * _ROW_H
        row_y2 = row_y + _ROW_H

        # Alternate row background
        if i % 2 == 1:
            d.rectangle([(0, row_y), (_W - 1, row_y2 - 1)], fill=_SURFACE)

        # Row separator
        d.line([(0, row_y2 - 1), (_W - 1, row_y2 - 1)], fill=_BORDER, width=1)

        # Label — left, vertically centred
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
        d.text((vx, vy), value, font=_FONT_VALUE, fill=_TEXT_PRIMARY)

    # Footer
    footer_y = _HEADER_H + _ROW_COUNT * _ROW_H
    d.rectangle([(0, footer_y), (_W - 1, _H - 1)], fill=_SURFACE)
    d.line([(0, footer_y), (_W - 1, footer_y)], fill=_BORDER, width=1)
    time_str = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    _draw_centered(d, time_str, footer_y, _H, _FONT_FOOTER, _ACCENT)


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
