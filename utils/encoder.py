"""
KY-040 rotary encoder wrapper.

Uses lgpio directly for reliable edge-triggered callbacks on Raspberry Pi 5.
gpiozero's RotaryEncoder has known issues with the lgpio backend on Pi 5 —
the when_rotated_* callbacks can fail to fire even though initialisation
succeeds.  Using lgpio directly bypasses this entirely.

Automatically tries gpiochip4 (Pi 5) then gpiochip0 (Pi 4 and earlier).
Falls back to a no-op stub when lgpio is unavailable (e.g. dev machines).

Wiring (verified):
    CLK (A) → GPIO17 (Pin 11)
    DT  (B) → GPIO27 (Pin 13)
    SW      → GPIO22 (Pin 15)
"""

from __future__ import annotations

import threading

try:
    import lgpio
    _LGPIO_AVAILABLE = True
except ImportError:
    _LGPIO_AVAILABLE = False


class KY040:
    """Thread-safe KY-040 rotary encoder using lgpio directly.

    Usage::

        enc = KY040()
        delta = enc.pop_delta()   # +N = CW steps, -N = CCW steps since last call
        pressed = enc.pop_press() # True if button was pressed since last call
    """

    CLK_GPIO = 17
    DT_GPIO  = 27
    SW_GPIO  = 22

    # Debounce in microseconds — reduces spurious edges from mechanical contacts
    _DEBOUNCE_US = 2_000

    def __init__(self) -> None:
        self._delta   = 0
        self._pressed = False
        self._lock    = threading.Lock()
        self._h       = None
        self._cbs: list = []

        if not _LGPIO_AVAILABLE:
            print("[encoder] lgpio not available — encoder disabled.")
            return

        for chip in (4, 0):  # Pi 5 = gpiochip4, Pi 4 = gpiochip0
            try:
                h = lgpio.gpiochip_open(chip)
                lgpio.gpio_claim_input(h, self.CLK_GPIO, lgpio.SET_PULL_UP)
                lgpio.gpio_claim_input(h, self.DT_GPIO,  lgpio.SET_PULL_UP)
                lgpio.gpio_claim_input(h, self.SW_GPIO,  lgpio.SET_PULL_UP)
                lgpio.gpio_set_debounce_micros(h, self.CLK_GPIO, self._DEBOUNCE_US)
                lgpio.gpio_set_debounce_micros(h, self.SW_GPIO,  self._DEBOUNCE_US)
                self._cbs.append(
                    lgpio.callback(h, self.CLK_GPIO, lgpio.FALLING_EDGE, self._on_clk)
                )
                self._cbs.append(
                    lgpio.callback(h, self.SW_GPIO,  lgpio.FALLING_EDGE, self._on_sw)
                )
                self._h = h
                print(f"[encoder] KY-040 ready (lgpio gpiochip{chip}).")
                return
            except Exception as exc:
                print(f"[encoder] gpiochip{chip} failed ({exc}).")

        print("[encoder] All GPIO chips failed — encoder disabled.")

    # ------------------------------------------------------------------
    # Callbacks (called from lgpio background thread)
    # Signature: func(chip, gpio, level, tick)
    # ------------------------------------------------------------------

    def _on_clk(self, chip: int, gpio: int, level: int, tick: int) -> None:
        # CLK fell — read DT to determine direction
        dt = lgpio.gpio_read(self._h, self.DT_GPIO)
        with self._lock:
            if dt == 1:
                self._delta += 1   # clockwise
            else:
                self._delta -= 1   # counter-clockwise

    def _on_sw(self, chip: int, gpio: int, level: int, tick: int) -> None:
        with self._lock:
            self._pressed = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def pop_delta(self) -> int:
        """Return accumulated rotation steps and reset the counter.

        Positive → clockwise (next page).
        Negative → counter-clockwise (previous page).
        """
        with self._lock:
            d = self._delta
            self._delta = 0
        return d

    def pop_press(self) -> bool:
        """Return True if the button was pressed since the last call, then reset."""
        with self._lock:
            p = self._pressed
            self._pressed = False
        return p

    def close(self) -> None:
        """Release GPIO resources."""
        for cb in self._cbs:
            try:
                cb.cancel()
            except Exception:
                pass
        self._cbs.clear()
        if self._h is not None:
            lgpio.gpiochip_close(self._h)
            self._h = None
