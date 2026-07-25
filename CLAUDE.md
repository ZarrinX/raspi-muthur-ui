# CLAUDE.md

# Project Context

This repository contains software for a Raspberry Pi 5 connected to a Waveshare 2.4" SPI TFT display using the ILI9341 controller.

The display is used as a platform for:

- LCARS-inspired interfaces
- MU/TH/UR-inspired interfaces
- System monitoring dashboards
- Electronics lab instrumentation displays
- ESP32 telemetry dashboards
- Custom ZR-branded interfaces

Before making architectural decisions, review:

- README.md
- spec.md
- AGENTS.md

AGENTS.md contains important hardware discoveries and troubleshooting information that should not be rediscovered.

---

# Primary Development Goals

Prioritize:

1. Reliability
2. Readability
3. Maintainability
4. Low display flicker
5. Efficient SPI usage

Do not optimize for theoretical maximum frame rates unless explicitly requested.

---

# Hardware Assumptions

Assume:

- Raspberry Pi 5
- Debian 12 (Bookworm)
- Waveshare 2.4" SPI display
- ILI9341 controller
- No touch support

## Verified Wiring — ILI9341 Display

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

## Verified Wiring — KY-040 Rotary Encoder

| Encoder Pin | Raspberry Pi 5 | Notes |
|-------------|----------------|-------|
| VCC (+) | 3.3V | |
| GND | GND | |
| CLK (A) | GPIO23 (Pin 16) | Rotary pulse A |
| DT (B) | GPIO26 (Pin 37) | Rotary pulse B |
| SW | GPIO16 (Pin 36) | Push button |

No pin conflicts exist between the display and encoder.

The display wiring has already been validated.

Do not recommend alternate wiring unless specifically asked.

---

# Display Driver Policy

Preferred display stack:

```python
adafruit-circuitpython-rgb-display
Pillow
```

Avoid introducing:

- luma.lcd
- luma.core

unless a compelling reason exists.

These libraries were previously evaluated and rejected for this project.

---

# SPI Configuration

Use:

```python
baudrate=16000000
```

as the default SPI speed.

Higher speeds were tested and produced visible display flicker.

Do not increase SPI speeds without justification.

---

# Rendering Guidelines

Prefer:

```text
Static layout
+
Incremental updates
+
Small redraw regions
```

Avoid:

```text
Full-screen redraw every frame
```

unless the display content genuinely requires it.

Display flicker has already been identified as a major usability concern.

---

# User Interface Style

Preferred visual inspirations:

## Primary

Star Trek: Picard

Characteristics:

- Dark backgrounds
- Amber
- Burnt orange
- Teal
- Deep blues
- Muted magentas
- Modern Starfleet aesthetic

## Secondary

Alien MU/TH/UR

Characteristics:

- Industrial
- Functional
- Telemetry-heavy
- Dense information displays
- Retro-futuristic aesthetics

---

# Branding

Future interfaces should reserve space for:

- ZR logo
- ZR branding
- Custom startup screens

The logo asset may be added later.

Code should avoid hardcoding layouts that prevent future branding integration.

---

# Dashboard Data Sources

Preferred sources:

```python
psutil
socket
/sys/class/thermal/thermal_zone0/temp
```

Avoid introducing unnecessary dependencies when standard Python or psutil can provide the required data.

---

# Development Philosophy

When modifying code:

- Preserve working hardware configurations.
- Favor incremental improvements.
- Minimize dependency growth.
- Keep deployment simple.
- Document hardware-specific discoveries.

When uncertain:

- Choose the simpler solution.
- Avoid premature optimization.
- Avoid rewriting stable subsystems.

---

# Common Pitfalls

## GPIO Busy Errors

Do not recommend:

```text
GPIO8 / CE0
```

for display chip select.

The project uses:

```text
GPIO5
```

for display CS.

Refer to AGENTS.md for details.

---

## Flicker

Observed display flicker is usually caused by:

```python
display.image(...)
```

executed against the entire display every frame.

Investigate redraw strategy before modifying hardware or SPI configuration.

---

# Preferred Project Structure

```text
project/
├── README.md
├── spec.md
├── AGENTS.md
├── CLAUDE.md
├── assets/
│   ├── logos/
│   ├── fonts/
│   └── images/
├── dashboards/
├── displays/
├── telemetry/
├── utils/
└── tests/
```

---

# Success Criteria

Successful contributions should:

- Improve maintainability
- Improve user experience
- Reduce display flicker
- Preserve verified hardware functionality

---

# Deployment

## Overview

This project deploys to two Raspberry Pis via Jenkins SSH pipelines. Each Pi has its own git branch and its own Jenkins job. Hardware is consistent across both Pis; UI and dashboards may differ between branches.

Do not suggest manual deployment steps as a permanent solution. All changes that affect runtime behaviour must be reflected in the appropriate `Jenkinsfile`.

## Deploy targets

| Branch | Name | Model | Host | Jenkinsfile |
|--------|------|-------|------|-------------|
| `main` | MUTHUR | Raspberry Pi 5 | 10.64.32.100 | `Jenkinsfile` |
| `TARS` | TARS | Raspberry Pi 4 | 10.64.32.101 | `Jenkinsfile.tars` → renamed to `Jenkinsfile` on that branch |

Both Pis use:

```
User:  zrice
Path:  /opt/raspi-muthur-ui
SSH credential: pi-ssh-key
```

Shared hardware changes (drivers, wiring, service templates) should be merged into both branches. UI/dashboard changes can remain branch-specific.

## Pipeline stages

1. **Checkout** — checks out the repo from GitHub
2. **Deploy** — rsyncs the workspace to the Pi (excludes `.git`, `venv`, `__pycache__`, `*.pyc`)
3. **Install Dependencies** — creates/updates the venv at `/opt/raspi-muthur-ui/venv/` and runs `pip install -r requirements.txt`
4. **Install Service Units** — copies `.service` files to `/etc/systemd/system/`, runs `daemon-reload` and `enable`
5. **Restart Services** — restarts all managed systemd services

## Python environment

The Pi uses a venv at `/opt/raspi-muthur-ui/venv/`.

All new dependencies must be added to `requirements.txt`. Do not assume system-wide packages are available.

## Systemd services

Each long-running process gets its own `.service` file in the repo root, following the naming pattern `raspi-muthur-ui-<name>.service`.

Current services:

| File | ExecStart | Purpose |
|------|-----------|---------|
| `raspi-muthur-ui.service` | `venv/bin/python main.py` | ILI9341 SPI telemetry dashboard |
| `raspi-muthur-ui-network.service` | `venv/bin/python -m dashboards.network` | HD44780 I2C network monitor |

When adding a new long-running dashboard or process:

1. Create a `raspi-muthur-ui-<name>.service` file using the existing files as a template.
2. Add a `SERVICE_<NAME>` environment variable in the `Jenkinsfile` `environment` block.
3. Add the new service to the `Install Service Units` and `Restart Services` stages in `Jenkinsfile`.

## sudoers

The deploy user `zrice` has the following passwordless sudo permission on the Pi:

```
zrice   ALL=(ALL) NOPASSWD: /bin/systemctl *
```

This covers `daemon-reload`, `enable`, and `restart` as used by the pipeline.

## Logs

Service logs are written to the systemd journal. To tail logs on the Pi:

```bash
journalctl -u raspi-muthur-ui -f
journalctl -u raspi-muthur-ui-network -f
```
- Support future ZR-branded interfaces
- Support future LCARS and MU/TH/UR-inspired dashboards

If a proposed change risks hardware stability, software simplicity, or display reliability, prefer the existing implementation unless there is a clear benefit.