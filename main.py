"""
raspi-muthur-ui — entrypoint.

Initialises the ILI9341 display, draws the static layout once,
then enters the telemetry tick loop updating only changed regions.
"""

import sys
import time

import dashboards.system as system_dashboard
from displays.ili9341 import get_display

TICK_INTERVAL_S = 2.0


def main() -> None:
    print("raspi-muthur-ui starting...")

    display = get_display()
    print("Display initialised.")

    system_dashboard.init(display)
    print(f"Static layout drawn. Ticking every {TICK_INTERVAL_S}s.")

    while True:
        try:
            system_dashboard.update()
        except KeyboardInterrupt:
            print("\nShutting down.")
            sys.exit(0)
        except Exception as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)

        time.sleep(TICK_INTERVAL_S)


if __name__ == "__main__":
    main()
