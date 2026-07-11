"""
Network I/O dashboard for the HD44780 1602 I2C character display.

Layout (16×2):
    ┌────────────────┐
    │ Sent:  0.00 Mb │  row 0 — Megabits transmitted since last tick
    │ Recv:  0.00 Mb │  row 1 — Megabits received since last tick
    └────────────────┘

Values are the Megabit delta between ticks, not cumulative totals.
"""

from __future__ import annotations

import sys
import time

from displays.hd44780 import HD44780I2C
from utils.telemetry import net_io_total_mb

TICK_INTERVAL_S: float = 2.0


def _format_mb(value: float) -> str:
    """Format a Megabit value to fit in 16 columns alongside the label.

    Label is 6 chars ("Sent: " / "Recv: "), value field is 7 chars
    ("{value:.2f}"), unit is 3 chars (" Mb") → 6 + 7 + 3 = 16 total.
    """
    return f"{value:7.2f} Mb"


def run(
    bus: int = 1,
    address: int = 0x27,
    tick_interval: float = TICK_INTERVAL_S,
) -> None:
    """Start the network monitor loop. Blocks until KeyboardInterrupt."""
    lcd = HD44780I2C(bus=bus, address=address)

    print(
        f"Network monitor running on I2C bus {bus}, address {hex(address)}. "
        f"Updating every {tick_interval}s. Press Ctrl+C to stop."
    )

    try:
        while True:
            try:
                sent_mb, recv_mb = net_io_total_mb()
                lcd.write_line(0, "Sent:" + _format_mb(sent_mb))
                lcd.write_line(1, "Recv:" + _format_mb(recv_mb))
            except Exception as exc:
                print(f"[ERROR] {exc}")
                lcd.write_line(0, "Error:")
                lcd.write_line(1, str(exc)[:16])
            time.sleep(tick_interval)
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        lcd.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Network I/O monitor on HD44780 I2C LCD")
    parser.add_argument("--bus", type=int, default=1, help="I2C bus number (default: 1)")
    parser.add_argument(
        "--address",
        type=lambda x: int(x, 0),
        default=0x27,
        help="I2C address in hex, e.g. 0x27 or 0x3F (default: 0x27)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=TICK_INTERVAL_S,
        help=f"Seconds between updates (default: {TICK_INTERVAL_S})",
    )
    args = parser.parse_args()
    run(bus=args.bus, address=args.address, tick_interval=args.interval)
    sys.exit(0)
