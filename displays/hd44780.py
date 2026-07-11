"""
HD44780 character LCD driver over I2C via a PCF8574 I/O expander.

Targets the common PCF8574 backpack wiring used by most HD44780 1602
modules. If your backpack uses a different pin map, adjust PCF8574_MAP.
"""

from __future__ import annotations

import time

from smbus2 import SMBus


PCF8574_MAP: dict[str, int] = {
    "rs":        0x01,
    "rw":        0x02,
    "e":         0x04,
    "backlight": 0x08,
    "d4":        0x10,
    "d5":        0x20,
    "d6":        0x40,
    "d7":        0x80,
}


class HD44780I2C:
    """Minimal HD44780 driver that communicates through a PCF8574 I2C expander."""

    def __init__(
        self,
        bus: int = 1,
        address: int = 0x27,
        cols: int = 16,
        rows: int = 2,
        backlight_active_low: bool = True,
    ) -> None:
        self.bus = SMBus(bus)
        self.address = address
        self.cols = cols
        self.rows = rows
        self.backlight = True
        self.backlight_active_low = backlight_active_low
        self.pins = PCF8574_MAP
        self._init_display()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def close(self) -> None:
        try:
            self.clear()
        finally:
            self.bus.close()

    def clear(self) -> None:
        self.command(0x01)
        time.sleep(0.002)

    def home(self) -> None:
        self.command(0x02)
        time.sleep(0.002)

    def set_cursor(self, col: int, row: int) -> None:
        row_offsets = [0x00, 0x40, 0x14, 0x54]
        row = max(0, min(self.rows - 1, row))
        self.command(0x80 | (col + row_offsets[row]))

    def write_line(self, row: int, text: str) -> None:
        """Write *text* to *row*, padding or truncating to fit the column count."""
        padded = text.ljust(self.cols)[: self.cols]
        self.set_cursor(0, row)
        for ch in padded:
            self.write_char(ord(ch))

    def command(self, cmd: int) -> None:
        self._send(cmd, mode=0)

    def write_char(self, value: int) -> None:
        self._send(value, mode=self.pins["rs"])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_backlight(self, value: int) -> int:
        if self.backlight_active_low:
            return (value & ~self.pins["backlight"]) if self.backlight else (value | self.pins["backlight"])
        return (value | self.pins["backlight"]) if self.backlight else (value & ~self.pins["backlight"])

    def _write_byte(self, value: int) -> None:
        self.bus.write_byte(self.address, self._apply_backlight(value))

    def _pack_nibble(self, nibble: int, mode: int = 0) -> int:
        value = mode & self.pins["rs"]
        value |= mode & self.pins["rw"]
        for bit_index, pin_name in enumerate(("d4", "d5", "d6", "d7")):
            if nibble & (1 << bit_index):
                value |= self.pins[pin_name]
        return value

    def _pulse_enable(self, value: int) -> None:
        self._write_byte(value | self.pins["e"])
        time.sleep(0.0005)
        self._write_byte(value & ~self.pins["e"])
        time.sleep(0.0001)

    def _write4bits(self, nibble: int, mode: int = 0) -> None:
        value = self._pack_nibble(nibble, mode)
        self._write_byte(value)
        self._pulse_enable(value)

    def _send(self, data: int, mode: int = 0) -> None:
        self._write4bits((data >> 4) & 0x0F, mode)
        self._write4bits(data & 0x0F, mode)

    def _init_display(self) -> None:
        time.sleep(0.05)
        self._write4bits(0x03)
        time.sleep(0.005)
        self._write4bits(0x03)
        time.sleep(0.0002)
        self._write4bits(0x03)
        time.sleep(0.0002)
        self._write4bits(0x02)
        self.command(0x28)  # 4-bit mode, 2 lines, 5×8 font
        self.command(0x08)  # display off
        self.clear()
        self.command(0x06)  # entry mode: increment, no shift
        self.command(0x0C)  # display on, cursor off, blink off
