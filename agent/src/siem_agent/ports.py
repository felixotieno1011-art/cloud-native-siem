"""Port and connection detection, Android/Termux-safe.

Two strategies, tried in order:
1. /proc/net/tcp[6]   — fast, works on Linux. Blocked by SELinux on Android.
2. Active local scan  — tries socket.connect on a curated port list.
                        Works on any Android, no root, no netlink.
"""

import socket
from dataclasses import dataclass, asdict
from typing import Any


# Common service ports worth watching on a phone/server.
SCAN_PORTS: tuple[int, ...] = (
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139,
    143, 443, 445, 465, 587, 631, 993, 995,
    1433, 1521, 2049, 2375, 2376, 3306, 3389,
    5432, 5900, 6379, 8000, 8022, 8080, 8081,
    8443, 8765, 8888, 9000, 9090, 9200, 9300,
    27017,
)


@dataclass
class SocketEntry:
    """A discovered socket (either from /proc or from a connect scan)."""
    protocol: str
    local_ip: str
    local_port: int
    remote_ip: str
    remote_port: int
    state: str
    uid: int
    inode: str
    source: str = "proc"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TCP_STATES = {
    "01": "ESTABLISHED", "02": "SYN_SENT", "03": "SYN_RECV",
    "04": "FIN_WAIT1", "05": "FIN_WAIT2", "06": "TIME_WAIT",
    "07": "CLOSE", "08": "CLOSE_WAIT", "09": "LAST_ACK",
    "0A": "LISTEN", "0B": "CLOSING",
}


def _hex_to_ipv4(hex_addr: str) -> str:
    import struct
    packed = bytes.fromhex(hex_addr)
    return socket.inet_ntoa(struct.pack("<I", struct.unpack(">I", packed)[0]))


def _hex_to_ipv6(hex_addr: str) -> str:
    packed = bytes.fromhex(hex_addr)
    reordered = b"".join(packed[i : i + 4][::-1] for i in range(0, 16, 4))
    return socket.inet_ntop(socket.AF_INET6, reordered)


def _parse_addr(addr: str, is_v6: bool) -> tuple[str, int]:
    hex_ip, _, hex_port = addr.partition(":")
    ip = _hex_to_ipv6(hex_ip) if is_v6 else _hex_to_ipv4(hex_ip)
    return ip, int(hex_port, 16)


def _read_tcp_file(path: str, is_v6: bool) -> list[SocketEntry]:
    entries: list[SocketEntry] = []
    try:
        with open(path) as f:
            next(f, None)
            for line in f:
                parts = line.split()
                if len(parts) < 10:
                    continue
                try:
                    lip, lport = _parse_addr(parts[1], is_v6)
                    rip, rport = _parse_addr(parts[2], is_v6)
                    entries.append(SocketEntry(
                        protocol="tcp6" if is_v6 else "tcp",
                        local_ip=lip, local_port=lport,
                        remote_ip=rip, remote_port=rport,
                        state=TCP_STATES.get(parts[3], parts[3]),
                        uid=int(parts[7]), inode=parts[9], source="proc",
                    ))
                except (ValueError, IndexError):
                    continue
    except (OSError, PermissionError):
        pass
    return entries


def _scan_localhost(ports: tuple[int, ...] = SCAN_PORTS, timeout: float = 0.15) -> list[SocketEntry]:
    """Connect-scan 127.0.0.1 for open TCP ports."""
    entries: list[SocketEntry] = []
    for port in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect(("127.0.0.1", port))
            entries.append(SocketEntry(
                protocol="tcp", local_ip="127.0.0.1", local_port=port,
                remote_ip="", remote_port=0, state="LISTEN",
                uid=-1, inode="", source="scan",
            ))
        except (ConnectionRefusedError, socket.timeout, OSError):
            pass
        finally:
            s.close()
    return entries


def collect_sockets() -> list[SocketEntry]:
    """Collect sockets via /proc, fall back to connect scan if blocked."""
    proc = _read_tcp_file("/proc/net/tcp", False) + _read_tcp_file("/proc/net/tcp6", True)
    if proc:
        return proc
    return _scan_localhost()


def listening_ports() -> list[int]:
    """Sorted unique local ports in LISTEN state."""
    return sorted({s.local_port for s in collect_sockets() if s.state == "LISTEN"})
