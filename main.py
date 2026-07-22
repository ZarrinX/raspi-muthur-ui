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

    encoder = KY040()
    print("Encoder initialised.")

    current_page = 0

    # Prime all dashboards with the display handle so each has its Image/Draw
    # allocated.  Only the active page will be pushed each tick.
    for i, dash in enumerate(_PAGES):
        dash.init(display, page_info=(i + 1, _TOTAL_PAGES))

    # Push the first page
    _PAGES[current_page].update(page_info=(current_page + 1, _TOTAL_PAGES))
    print(f"Static layout drawn. Ticking every {TICK_INTERVAL_S}s.")

    while True:
        try:
            delta = encoder.pop_delta()
            if delta != 0:
                direction = 1 if delta > 0 else -1
                current_page = (current_page + direction) % _TOTAL_PAGES
                print(f"Page → {current_page + 1}/{_TOTAL_PAGES}")

            _PAGES[current_page].update(page_info=(current_page + 1, _TOTAL_PAGES))

        except KeyboardInterrupt:
            print("\nShutting down.")
            encoder.close()
            sys.exit(0)
        except Exception as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)

        time.sleep(TICK_INTERVAL_S)


if __name__ == "__main__":
    main()

