"""
raspi-muthur-ui — entrypoint.

Initialises the ILI9341 display and the KY-040 rotary encoder, draws the
static layout for the active page, then enters the telemetry tick loop.

Pages
-----
  0 — System telemetry  (CPU / RAM / Disk / Temp / IP)
  1 — Network info      (Hostname / RX / TX / SSH / Top process)

Rotating the encoder clockwise advances to the next page; counter-clockwise
goes back.  The active page wraps around.  The header of every page shows a
"#/#" indicator in the top-right corner.
"""

import sys
import time

import dashboards.network_page as network_dashboard
import dashboards.system as system_dashboard
from displays.ili9341 import get_display
from utils.encoder import KY040

TICK_INTERVAL_S   = 2.0   # display refresh rate
ENCODER_POLL_S    = 0.1   # encoder check rate (~10 Hz)

_PAGES = [system_dashboard, network_dashboard]
_TOTAL_PAGES = len(_PAGES)


def main() -> None:
    print("raspi-muthur-ui starting...")

    display = get_display()
    print("Display initialised.")

    try:
        encoder = KY040()
    except Exception as exc:
        print(f"[WARN] Encoder unavailable: {exc} — continuing without encoder.")
        encoder = None

    current_page  = 0
    _initialised  = set()   # tracks which page indices have been init'd

    def _ensure_init(page_idx: int) -> None:
        if page_idx not in _initialised:
            _PAGES[page_idx].init(display, page_info=(page_idx + 1, _TOTAL_PAGES))
            _initialised.add(page_idx)

    def _change_page(new_page: int, reason: str) -> None:
        nonlocal current_page
        current_page = new_page
        print(f"Page → {current_page + 1}/{_TOTAL_PAGES} ({reason})")
        _ensure_init(current_page)
        _PAGES[current_page].update(page_info=(current_page + 1, _TOTAL_PAGES))

    _ensure_init(current_page)
    print(f"Static layout drawn. Display refresh every {TICK_INTERVAL_S}s, encoder polled every {ENCODER_POLL_S}s.")

    last_tick = time.monotonic()

    while True:
        try:
            now = time.monotonic()

            # Check encoder every ENCODER_POLL_S
            if encoder is not None:
                if encoder.pop_press():
                    _change_page((current_page + 1) % _TOTAL_PAGES, "button")

                delta = encoder.pop_delta()
                if delta != 0:
                    direction = 1 if delta > 0 else -1
                    _change_page((current_page + direction) % _TOTAL_PAGES, "knob")

            # Refresh display at TICK_INTERVAL_S
            if now - last_tick >= TICK_INTERVAL_S:
                _PAGES[current_page].update(page_info=(current_page + 1, _TOTAL_PAGES))
                last_tick = now

        except KeyboardInterrupt:
            print("\nShutting down.")
            if encoder is not None:
                encoder.close()
            sys.exit(0)
        except Exception as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)

        time.sleep(ENCODER_POLL_S)


if __name__ == "__main__":
    main()

