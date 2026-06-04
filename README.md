# Raspberry Pi 5 + Waveshare ILI9341 SPI Display

Proof-of-concept project demonstrating a Waveshare 2.4" ILI9341 SPI TFT display connected to a Raspberry Pi 5 running Debian 12 (Bookworm).

The project was developed as a hardware validation platform and foundation for MU/TH/UR-inspired dashboard interfaces.

---

# Goals

- Verify Raspberry Pi 5 SPI operation
- Verify compatibility with Waveshare ILI9341 displays
- Evaluate Python graphics libraries
- Prototype MU/TH/UR-inspired interfaces
- Develop a foundation for future dashboard applications

---

# Hardware

## Host

- Raspberry Pi 5
- Debian 12 (Bookworm)

## Display

- Waveshare 2.4" SPI TFT
- ILI9341 controller
- Display-only model (no touch controller)

---

# Wiring

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
| MISO | Optional |

## Important

Do **not** connect CS to GPIO8 / CE0 (Pin 24) when using the Adafruit CircuitPython display driver.

Using CE0 caused:

```text
lgpio.error: 'GPIO busy'
```

The Linux SPI subsystem already owns CE0 on the Raspberry Pi 5.

Use GPIO5 instead.

---

# Software

## Virtual Environment

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

## Install Dependencies

```bash
pip install adafruit-circuitpython-rgb-display
pip install pillow
pip install psutil
```

---

# SPI Verification

Verify SPI is enabled:

```bash
ls -l /dev/spidev*
```

Expected:

```text
/dev/spidev0.0
/dev/spidev0.1
/dev/spidev10.0
```

---

# Display Driver Evaluation

## Luma LCD

Initially tested:

```text
luma.lcd
luma.core
```

Findings:

- Works on many older Raspberry Pi platforms.
- Additional compatibility issues encountered on Raspberry Pi 5.
- Dependency complications involving GPIO libraries.

Decision:

- Not used for final implementation.

## Adafruit RGB Display

Selected for the proof of concept.

Benefits:

- Simple setup
- Good Raspberry Pi 5 compatibility
- Active maintenance
- Easy integration with Pillow graphics

---

# Performance Findings

## SPI Clock Rates

### 40 MHz

Pros:

- Fast transfers

Cons:

- Visible flicker during full-screen redraws

### 24 MHz

Pros:

- Improved stability

Cons:

- Some redraw artifacts remained

### 16 MHz

Pros:

- Best overall visual quality
- Stable operation

Current recommendation:

```python
baudrate=16000000
```

---

# Display Behavior

## Flicker

Observed during animated dashboard updates.

Cause:

```python
display.image(render(frame))
```

The entire display image is transmitted every frame.

This results in:

- Increased SPI traffic
- Visible refresh artifacts
- Perceived screen pulsing

Backlight testing confirmed that the issue is not related to display illumination.

---

# Demonstrated Features

The proof-of-concept dashboard successfully demonstrated:

- MU/TH/UR-inspired visual elements
- Animated status indicators
- CPU utilization
- Memory utilization
- Disk utilization
- CPU temperature monitoring
- Network information display

---

# Future Plans

Potential applications include:

- ZR Operations Console
- MU/TH/UR terminal interface
- Electronics lab dashboard
- LoRa telemetry monitor
- ESP32 project monitor
- Raspberry Pi system monitor

---

# Lessons Learned

1. Raspberry Pi 5 SPI support works well with the ILI9341.
2. GPIO5 is preferred over CE0 when using the Adafruit driver.
3. Full-screen redraws can create visible flicker.
4. Partial updates are preferred for production dashboards.
5. The Adafruit display stack is currently the simplest solution for Raspberry Pi 5 + ILI9341 development.

---

# Status

Proof of concept completed successfully.

Hardware validated.  
Software stack validated.  
Ready for application-specific development.