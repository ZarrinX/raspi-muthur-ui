"""
System telemetry helpers.

All values are read from psutil and /sys/class/thermal/thermal_zone0/temp.
No external network calls — suitable for offline operation.
"""

from __future__ import annotations

import socket

import psutil


def cpu_percent() -> float:
    """Return current CPU usage as a percentage (0.0–100.0)."""
    return psutil.cpu_percent(interval=None)


def ram_percent() -> float:
    """Return current RAM usage as a percentage (0.0–100.0)."""
    return psutil.virtual_memory().percent


def disk_percent(path: str = "/") -> float:
    """Return disk usage for *path* as a percentage (0.0–100.0)."""
    return psutil.disk_usage(path).percent


def cpu_temp() -> float | None:
    """Return CPU temperature in Celsius, or None if unavailable."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return int(f.read().strip()) / 1000.0
    except OSError:
        return None


def ip_address() -> str:
    """Return the primary non-loopback IP address, or 'unavailable'."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "unavailable"
