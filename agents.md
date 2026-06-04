# AGENTS.md

# Raspberry Pi 5 + Waveshare ILI9341 Project Guidance

This document captures project-specific knowledge discovered during development.

Future agents working on this project should read this file before making hardware, software, or architectural recommendations.

---

# Project Overview

This project uses:

- Raspberry Pi 5
- Debian 12 (Bookworm)
- Waveshare 2.4" SPI TFT
- ILI9341 display controller
- Display-only model (no touch controller)

The display is used for dashboard and UI experimentation, including:

- LCARS-style interfaces
- MU/TH/UR-inspired interfaces
- System monitoring
- Electronics lab dashboards
- ESP32 telemetry displays

---

# Verified Hardware Configuration

## Wiring

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

---

# Critical Discovery: CS Pin

## DO NOT USE CE0

The display was originally connected to:

```text
GPIO8 / CE0 / Pin 24
```

This caused:

```text
lgpio.error: 'GPIO busy'
```

Reason:

- Linux SPI owns CE0.
- Adafruit Blinka attempts to claim CS as a GPIO.
- Resource conflict occurs.

## Required Configuration

Display CS must be connected to:

```text
GPIO5 / Pin 29
```

and software must use:

```python
cs_pin = digitalio.DigitalInOut(board.D5)
```

Future agents should not recommend CE0 for this project.

---

# SPI Configuration

SPI is enabled and operational.

Expected devices:

```text
/dev/spidev0.0
/dev/spidev0.1
/dev/spidev10.0
```

Verification command:

```bash
ls -l /dev/spidev*
```

---

# Display Driver Selection

## Rejected

### luma.lcd

Previously evaluated.

Issues:

- RPi.GPIO dependency
- Additional compatibility issues on Raspberry Pi 5
- Higher setup complexity

Do not recommend luma.lcd unless there is a compelling project-specific reason.

---

## Approved

### Adafruit RGB Display

Current preferred display stack.

Libraries:

```bash
pip install adafruit-circuitpython-rgb-display
pip install pillow
```

Advantages:

- Verified working
- Simpler setup
- Better Raspberry Pi 5 compatibility
- Easier integration with Pillow graphics

---

# Performance Findings

## SPI Clock Rate Testing

### 40 MHz

Functional.

Observed:

- Noticeable flicker
- Visible display pulsing

### 24 MHz

Improved.

Still exhibited some redraw artifacts.

### 16 MHz

Current recommended setting.

Configuration:

```python
baudrate=16000000
```

This produced the best balance of:

- Stability
- Visual quality
- Reliability

Future agents should default to 16 MHz unless there is evidence a higher rate is beneficial.

---

# Display Flicker Findings

## Root Cause

Not a backlight issue.

Backlight is tied directly to 3.3V.

Observed pulsing is caused by:

```python
display.image(render(frame))
```

when transmitting full-screen images repeatedly.

The bottleneck is:

- Full-screen SPI redraws

Not:

- Backlight
- Wiring
- Power delivery

---

# Recommended Rendering Strategy

Preferred:

```text
Static UI
+
Partial updates
+
Small redraw regions
```

Avoid:

```text
Full-screen redraw every frame
```

unless required.

---

# UI Design Direction

Preferred visual inspirations:

## Star Trek Picard

Use:

- Dark backgrounds
- Burnt orange
- Amber
- Teal
- Muted magenta
- Deep blues

Avoid:

- Bright TNG-era rainbow LCARS

---

## Alien MU/TH/UR

Use:

- Industrial styling
- Dense telemetry
- Diagnostic displays
- Retro CRT-inspired aesthetics
- Functional layouts

---

## ZR Branding

Future interfaces should incorporate:

- ZR logo
- MU/TH/UR-inspired styling
- Custom diagnostics panels

The exact ZR logo asset may be supplied later.

Design layouts should anticipate logo placement.

---

# Dashboard Data Sources

Verified usable:

```python
psutil.cpu_percent()
psutil.virtual_memory()
psutil.disk_usage("/")
```

CPU temperature:

```python
/sys/class/thermal/thermal_zone0/temp
```

IP discovery:

```python
socket
```

Future agents may safely use these sources.

---

# Common Failure Modes

## GPIO Busy

Symptom:

```text
lgpio.error: 'GPIO busy'
```

Likely causes:

- CE0 used for display CS
- Previous Python process still running

Resolution:

```bash
pkill -f python
```

or:

```bash
sudo reboot
```

---

## Blank Display

Verify:

- BL connected to 3.3V
- SPI enabled
- GPIO5 used for CS
- DC on GPIO25
- RESET on GPIO24

---

## Flicker

Check:

- SPI baud rate
- Full-screen redraw frequency

Recommended first action:

```python
baudrate=16000000
```

---

# Future Development Recommendations

Priority order:

1. Partial redraw architecture
2. Dashboard framework
3. ZR branding integration
4. System monitor
5. ESP32 telemetry integration
6. Lab instrumentation dashboard
7. Advanced LCARS/MU-TH-UR interface system

---

# Project Status

Hardware validated.

Software stack validated.

Display operational.

Ready for application-specific development.