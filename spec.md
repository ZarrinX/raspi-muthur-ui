# Raspberry Pi 5 + Waveshare ILI9341 SPI Display Proof of Concept

## Hardware

### Host System
- Raspberry Pi 5
- Debian 12 (Bookworm)

### Display
- Waveshare 2.4" SPI TFT
- Controller: ILI9341
- Display only (no touch controller)

## Verified Wiring

| Display Pin | Raspberry Pi 5 |
|------------|----------------|
| VCC | 3.3V |
| GND | GND |
| DIN (MOSI) | GPIO10 (Pin 19) |
| CLK (SCLK) | GPIO11 (Pin 23) |
| CS | GPIO5 (Pin 29) |
| DC | GPIO25 (Pin 22) |
| RST | GPIO24 (Pin 18) |
| BL | 3.3V |
| MISO | Optional / Not Required |

### Important Note

The display CS line was originally connected to:

```text
GPIO8 / CE0 (Pin 24)
```

This caused:

```text
lgpio.error: 'GPIO busy'
```

Reason:

- GPIO8/CE0 is controlled by the Linux SPI subsystem on Raspberry Pi 5.
- The Adafruit CircuitPython display driver attempts to claim CS as a normal GPIO.
- This results in a resource conflict.

### Final Solution

Move CS from:

```text
GPIO8 / Pin 24
```

to:

```text
GPIO5 / Pin 29
```

and configure:

```python
cs_pin = digitalio.DigitalInOut(board.D5)
```

---

## Software Stack

### Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Libraries

```bash
pip install adafruit-circuitpython-rgb-display
pip install pillow
pip install psutil
```

---

## SPI Verification

SPI successfully enabled and verified.

Expected devices:

```text
/dev/spidev0.0
/dev/spidev0.1
/dev/spidev10.0
```

---

## Display Driver Findings

### Luma LCD

Initial testing used:

```text
luma.lcd
luma.core
```

Issues encountered:

- Dependency on RPi.GPIO
- Compatibility complications on Raspberry Pi 5
- Additional configuration requirements

Decision:

- Abandoned in favor of Adafruit RGB Display driver.

### Adafruit RGB Display

Successfully initialized display.

Verified functionality:

- Screen clear
- Text rendering
- Shape rendering
- Full-screen image updates

---

## Performance Findings

### SPI Clock Rates

#### 40 MHz

Display operated but exhibited visible flicker/pulsing during full-screen updates.

#### 24 MHz

Improved stability.

#### 16 MHz

Best overall visual result.

Configuration:

```python
baudrate=16000000
```

Current recommendation:

```python
baudrate=16000000
```

---

## Flicker Analysis

Observed behavior:

- Visible screen pulsing during animated dashboard updates.

Root cause:

```python
display.image(render(frame))
```

This causes:

- Full-screen redraws
- SPI saturation
- Visible refresh artifacts

Reducing frame rate reduced flicker, confirming redraw behavior rather than backlight instability.

### Backlight Findings

Backlight connected directly to 3.3V.

Observed behavior inconsistent with backlight issues.

Conclusion:

- Flicker is software redraw related.
- Not a backlight problem.

---

## Dashboard Proof of Concept

Successfully demonstrated:

- Picard-inspired LCARS styling
- MU/TH/UR-inspired interface elements
- Animated status indicators
- System telemetry
- CPU usage
- RAM usage
- Disk usage
- CPU temperature
- IP address display

---

## Future Direction

Current implementation serves as a proof of concept only.

Recommended architecture for future development:

- Draw static UI elements once.
- Update only changing regions.
- Avoid full-screen redraws.
- Cache infrequently changing data.
- Use region-based rendering for smooth updates.

Potential future interfaces:

- ZR command console
- MU/TH/UR terminal
- System diagnostics panel
- Electronics lab dashboard
- LoRa telemetry display
- ESP32 project monitor
- Custom Starfleet-style operations console

---

## Lessons Learned

1. Raspberry Pi 5 SPI support works correctly with the ILI9341.
2. GPIO5 is preferred over CE0 when using the Adafruit CircuitPython driver.
3. Full-screen redraws create visible flicker on SPI TFT displays.
4. Partial updates are preferred for production dashboards.
5. The Adafruit display stack is currently the simplest solution for Raspberry Pi 5 + ILI9341 development.
6. 16 MHz SPI provides the best balance between speed and visual stability in the current setup.

---

## Status

**Proof of concept successful.**

- Hardware validated
- Wiring validated
- SPI validated
- Software stack validated
- Display driver validated
- Ready for application-specific development