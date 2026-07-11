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


def net_io_total_mb() -> tuple[float, float]:
    """Return (sent_mb, recv_mb) as cumulative Megabits since boot.

    1 Mb = 1,000,000 bits = 125,000 bytes.
    """
    counters = psutil.net_io_counters()
    if counters is None:
        raise RuntimeError("psutil.net_io_counters() returned None — no network interfaces found")
    sent_mb = counters.bytes_sent * 8 / 1_000_000
    recv_mb = counters.bytes_recv * 8 / 1_000_000
    return sent_mb, recv_mb


# Module-level state for net_io_delta_mb.
_last_net_bytes_sent: int | None = None
_last_net_bytes_recv: int | None = None


def net_io_delta_mb() -> tuple[float, float]:
    """Return (sent_mb, recv_mb) in Megabits transferred since the last call.

    On the first call the counters are seeded and (0.0, 0.0) is returned.
    Subsequent calls return the delta since the previous call.
    1 Mb = 1,000,000 bits = 125,000 bytes.
    """
    global _last_net_bytes_sent, _last_net_bytes_recv

    counters = psutil.net_io_counters()
    if counters is None:
        raise RuntimeError("psutil.net_io_counters() returned None — no network interfaces found")
    current_sent = counters.bytes_sent
    current_recv = counters.bytes_recv

    if _last_net_bytes_sent is None:
        _last_net_bytes_sent = current_sent
        _last_net_bytes_recv = current_recv
        return 0.0, 0.0

    sent_mb = (current_sent - _last_net_bytes_sent) * 8 / 1_000_000
    recv_mb = (current_recv - _last_net_bytes_recv) * 8 / 1_000_000

    _last_net_bytes_sent = current_sent
    _last_net_bytes_recv = current_recv

    return sent_mb, recv_mb
