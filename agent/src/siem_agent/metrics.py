"""System metrics collection, Android/Termux-safe."""

import os
import platform
import socket
import time
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class SystemMetrics:
    """Snapshot of system metrics."""
    hostname: str
    os: str
    arch: str
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    load_avg_1m: float
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_meminfo() -> dict[str, int]:
    """Parse /proc/meminfo into a dict of kB values (may be blocked)."""
    info: dict[str, int] = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                key, _, rest = line.partition(":")
                value = rest.strip().split()[0]
                info[key.strip()] = int(value)
    except (OSError, ValueError):
        pass
    return info


def _read_loadavg() -> float:
    """Read 1-minute load average from /proc/loadavg."""
    try:
        with open("/proc/loadavg") as f:
            return float(f.read().split()[0])
    except (OSError, ValueError, IndexError):
        return 0.0


def _memory_percent() -> float:
    info = _read_meminfo()
    total = info.get("MemTotal", 0)
    available = info.get("MemAvailable", info.get("MemFree", 0))
    if total == 0:
        return 0.0
    return round(100.0 * (total - available) / total, 2)


def _cpu_percent() -> float:
    """Approximate CPU% from load average / CPU count."""
    load1 = _read_loadavg()
    cpus = os.cpu_count() or 1
    return round(min(100.0, 100.0 * load1 / cpus), 2)


def _disk_percent(path: str = "/") -> float:
    try:
        st = os.statvfs(path)
    except OSError:
        return 0.0
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    if total == 0:
        return 0.0
    return round(100.0 * (total - free) / total, 2)


def get_system_metrics() -> SystemMetrics:
    """Collect current system metrics, Android/Termux-safe."""
    return SystemMetrics(
        hostname=socket.gethostname(),
        os=platform.system(),
        arch=platform.machine(),
        cpu_percent=_cpu_percent(),
        memory_percent=_memory_percent(),
        disk_percent=_disk_percent("/"),
        load_avg_1m=round(_read_loadavg(), 2),
        timestamp=time.time(),
    )
