"""
KY-040 rotary encoder wrapper.

Uses lgpio directly for reliable edge-triggered callbacks on Raspberry Pi 4.
gpiozero's RotaryEncoder has known issues with the lgpio backend — the
when_rotated_* callbacks can fail to fire even though initialisation succeeds.

TARS is a Pi 4. gpiochip0 is the main BCM GPIO header.
gpiochip4 also exists on Pi 4 (internal hardware) and must NOT be used —
claiming pins on it succeeds silently but they are not the physical GPIO pins.

Wiring (verified):
    CLK (A) → GPIO23 (Pin 16)
    DT  (B) → GPIO26 (Pin 37)
    SW      → GPIO16 (Pin 36)
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

    CLK_GPIO = 23
    DT_GPIO  = 26
    SW_GPIO  = 16

    def __init__(self) -> None:
        self._delta   = 0
        self._pressed = False
        self._lock    = threading.Lock()
        self._h       = None
        self._cbs: list = []

        if not _LGPIO_AVAILABLE:
            print("[encoder] lgpio not available — encoder disabled.")
            return

        # TARS is a Pi 4 — gpiochip0 is the main BCM GPIO header.
        # gpiochip4 also exists on Pi 4 (internal) and must NOT be used.
        try:
            h = lgpio.gpiochip_open(0)
            # Free pins first — a previous crashed run may have left them claimed
            for pin in (self.CLK_GPIO, self.DT_GPIO, self.SW_GPIO):
                try:
                    lgpio.gpio_free(h, pin)
                except Exception:
                    pass
            lgpio.gpio_claim_input(h, self.CLK_GPIO, lgpio.SET_PULL_UP)
            lgpio.gpio_claim_input(h, self.DT_GPIO,  lgpio.SET_PULL_UP)
            lgpio.gpio_claim_input(h, self.SW_GPIO,  lgpio.SET_PULL_UP)
            self._cbs.append(
                lgpio.callback(h, self.CLK_GPIO, lgpio.FALLING_EDGE, self._on_clk)
            )
            self._cbs.append(
                lgpio.callback(h, self.SW_GPIO,  lgpio.FALLING_EDGE, self._on_sw)
            )
            self._h = h
            print("[encoder] KY-040 ready (lgpio gpiochip0).")
        except Exception as exc:
            print(f"[encoder] GPIO init failed ({exc}) — encoder disabled.")

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
