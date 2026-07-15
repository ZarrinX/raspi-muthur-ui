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

try:
    import lgpio as _lgpio
    _LGPIO_AVAILABLE = True
except ImportError:
    _lgpio = None  # type: ignore[assignment]
    _LGPIO_AVAILABLE = False

from displays.hd44780 import HD44780I2C
from utils.telemetry import net_io_total_mb

TICK_INTERVAL_S: float = 2.0
BUTTON_GPIO: int = 26
DEBOUNCE_S: float = 0.05   # 50 ms
BUTTON_POLL_S: float = 0.02  # 20 ms poll interval within each tick


def _format_mb(value: float) -> str:
    """Format a Megabit value to fit in 16 columns alongside the label.

    Label is 5 chars ("Sent:" / "Recv:"), value+unit field is 11 chars.
    Auto-scales to Gb when value >= 1000 Mb.
    """
    if value >= 1000.0:
        return f"{value / 1000:7.2f} Gb"
    return f"{value:7.2f} Mb"


def _setup_button() -> tuple[object | None, int | None]:
    """Open the lgpio chip and claim GPIO *BUTTON_GPIO* as an input with pull-up.

    Returns ``(chip_handle, gpio_pin)`` on success, or ``(None, None)`` when
    lgpio is unavailable so the rest of the dashboard still runs.
    """
    if not _LGPIO_AVAILABLE:
        print("[WARN] lgpio not available — button support disabled.")
        return None, None
    try:
        h = _lgpio.gpiochip_open(0)
        _lgpio.gpio_claim_input(h, BUTTON_GPIO, _lgpio.SET_PULL_UP)
        print(f"Button configured on GPIO {BUTTON_GPIO} (pull-up).")
        return h, BUTTON_GPIO
    except Exception as exc:
        print(f"[WARN] Could not configure button GPIO {BUTTON_GPIO}: {exc}")
        return None, None


def run(
    bus: int = 1,
    address: int = 0x27,
    tick_interval: float = TICK_INTERVAL_S,
) -> None:
    """Start the network monitor loop. Blocks until KeyboardInterrupt."""
    lcd = HD44780I2C(bus=bus, address=address)
    chip, btn_pin = _setup_button()

    # Debounce state
    _last_raw: int = 1          # last sampled pin level (1 = released)
    _stable_level: int = 1      # last debounced level
    _last_change_time: float = 0.0

    print(
        f"Network monitor running on I2C bus {bus}, address {hex(address)}. "
        f"Updating every {tick_interval}s. Press Ctrl+C to stop."
    )

    try:
        next_update = time.monotonic()
        while True:
            now = time.monotonic()

            # --- button poll & debounce ---
            if chip is not None and btn_pin is not None:
                try:
                    raw = _lgpio.gpio_read(chip, btn_pin)
                except Exception:
                    raw = _last_raw

                if raw != _last_raw:
                    _last_raw = raw
                    _last_change_time = now

                # Signal is stable when it hasn't changed for DEBOUNCE_S
                if (now - _last_change_time) >= DEBOUNCE_S and _last_raw != _stable_level:
                    _stable_level = _last_raw
                    if _stable_level == 0:  # active-low: 0 means pressed
                        lcd.toggle_backlight()

            # --- display update ---
            if now >= next_update:
                next_update = now + tick_interval
                try:
                    sent_mb, recv_mb = net_io_total_mb()
                    lcd.write_line(0, "Sent:" + _format_mb(sent_mb))
                    lcd.write_line(1, "Recv:" + _format_mb(recv_mb))
                except Exception as exc:
                    print(f"[ERROR] {exc}")
                    lcd.write_line(0, "Error:")
                    lcd.write_line(1, str(exc)[:16])

            time.sleep(BUTTON_POLL_S)

    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        if chip is not None:
            try:
                _lgpio.gpiochip_close(chip)
            except Exception:
                pass
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
