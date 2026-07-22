"""
KY-040 rotary encoder wrapper.

Uses gpiozero's RotaryEncoder for quadrature decoding via callbacks so the
main loop never needs to poll GPIOs directly.  Falls back to a no-op stub
when gpiozero is unavailable (e.g. dev machines without GPIO hardware).

Wiring (verified):
    CLK (A) → GPIO17 (Pin 11)
    DT  (B) → GPIO27 (Pin 13)
    SW      → GPIO22 (Pin 15)
"""

from __future__ import annotations

import threading

try:
    from gpiozero import Button, RotaryEncoder

    _GPIOZERO_AVAILABLE = True
except ImportError:
    _GPIOZERO_AVAILABLE = False


class KY040:
    """Thread-safe KY-040 rotary encoder.

    Usage::

        enc = KY040()
        delta = enc.pop_delta()   # +N = CW steps, -N = CCW steps since last call
    """

    CLK_GPIO = 17
    DT_GPIO  = 27
    SW_GPIO  = 22

    def __init__(self) -> None:
        self._delta = 0
        self._lock  = threading.Lock()

        if _GPIOZERO_AVAILABLE:
            self._enc = RotaryEncoder(self.CLK_GPIO, self.DT_GPIO)
            self._enc.when_rotated_clockwise        = self._on_cw
            self._enc.when_rotated_counter_clockwise = self._on_ccw
            self._btn: Button | None = Button(
                self.SW_GPIO, pull_up=True, bounce_time=0.05
            )
        else:
            self._enc = None  # type: ignore[assignment]
            self._btn = None
            print("[encoder] gpiozero not available — encoder disabled.")

    # ------------------------------------------------------------------
    # Callbacks (called from gpiozero background thread)
    # ------------------------------------------------------------------

    def _on_cw(self) -> None:
        with self._lock:
            self._delta += 1

    def _on_ccw(self) -> None:
        with self._lock:
            self._delta -= 1

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

    def close(self) -> None:
        """Release GPIO resources."""
        if self._enc is not None:
            self._enc.close()
        if self._btn is not None:
            self._btn.close()
