"""
Display initialisation for the Waveshare 2.4" ILI9341 SPI TFT.

Verified wiring (from agents.md):
    CS  → GPIO5  / Pin 29   DO NOT use CE0/GPIO8 — causes 'GPIO busy' error
    DC  → GPIO25 / Pin 22
    RST → GPIO24 / Pin 18
    SPI → MOSI=GPIO10, SCLK=GPIO11

SPI baud rate: 16 MHz — higher rates cause visible flicker on this display.
"""

import board
import busio
import digitalio
import adafruit_rgb_display.ili9341 as ili9341

# 16 MHz is the verified sweet spot for this display.
# 24 MHz and 40 MHz were tested and produced visible flicker.
BAUDRATE = 16_000_000

DISPLAY_WIDTH  = 240
DISPLAY_HEIGHT = 320


def get_display() -> ili9341.ILI9341:
    """Initialise the ILI9341 and return the display object.

    Uses portrait orientation (240×320).
    CS is on GPIO5 — never GPIO8/CE0.
    """
    cs_pin    = digitalio.DigitalInOut(board.D5)
    dc_pin    = digitalio.DigitalInOut(board.D25)
    reset_pin = digitalio.DigitalInOut(board.D24)

    spi = busio.SPI(clock=board.SCLK, MOSI=board.MOSI)

    display = ili9341.ILI9341(
        spi,
        cs=cs_pin,
        dc=dc_pin,
        rst=reset_pin,
        baudrate=BAUDRATE,
        width=DISPLAY_WIDTH,
        height=DISPLAY_HEIGHT,
        rotation=180,  # portrait, rotated 180° — display is mounted upside down
    )
    return display
