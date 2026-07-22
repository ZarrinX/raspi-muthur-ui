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

TICK_INTERVAL_S = 2.0

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

    _ensure_init(current_page)
    print(f"Static layout drawn. Ticking every {TICK_INTERVAL_S}s.")

    while True:
        try:
            if encoder is not None:
                delta = encoder.pop_delta()
                if delta != 0:
                    direction = 1 if delta > 0 else -1
                    current_page = (current_page + direction) % _TOTAL_PAGES
                    print(f"Page → {current_page + 1}/{_TOTAL_PAGES}")
                    _ensure_init(current_page)

            _PAGES[current_page].update(page_info=(current_page + 1, _TOTAL_PAGES))

        except KeyboardInterrupt:
            print("\nShutting down.")
            if encoder is not None:
                encoder.close()
            sys.exit(0)
        except Exception as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)

        time.sleep(TICK_INTERVAL_S)


if __name__ == "__main__":
    main()

