"""Parse /proc/net/tcp[6] for listening ports and connections.

Android blocks `ss` and `netstat`, but /proc/net/tcp is world-readable.
Each line format (whitespace-separated):
  sl  local_address rem_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode
Address is HEX_IP:HEX_PORT (little-endian IPv4).
TCP state 0A = LISTEN, 01 = ESTABLISHED, 06 = TIME_WAIT, etc.
"""

import socket
import struct
from dataclasses import dataclass, asdict
from typing import Any


TCP_STATES = {
    "01": "ESTABLISHED",
    "02": "SYN_SENT",
    "03": "SYN_RECV",
    "04": "FIN_WAIT1",
    "05": "FIN_WAIT2",
    "06": "TIME_WAIT",
    "07": "CLOSE",
    "08": "CLOSE_WAIT",
    "09": "LAST_ACK",
    "0A": "LISTEN",
    "0B": "CLOSING",
}


@dataclass
class SocketEntry:
    """A single socket from /proc/net/tcp."""
    protocol: str
    local_ip: str
    local_port: int
    remote_ip: str
    remote_port: int
    state: str
    uid: int
    inode: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hex_to_ipv4(hex_addr: str) -> str:
    """Convert little-endian hex IPv4 address to dotted-quad."""
    packed = bytes.fromhex(hex_addr)
    return socket.inet_ntoa(struct.pack("<I", struct.unpack(">I", packed)[0]))


def _hex_to_ipv6(hex_addr: str) -> str:
    """Convert 32-hex-char IPv6 address to colon form."""
    packed = bytes.fromhex(hex_addr)
    # /proc stores IPv6 as 4 little-endian 32-bit words.
    reordered = b"".join(packed[i : i + 4][::-1] for i in range(0, 16, 4))
    return socket.inet_ntop(socket.AF_INET6, reordered)


def _parse_addr(addr: str, is_v6: bool) -> tuple[str, int]:
    """Split HEX_IP:HEX_PORT into (ip, port)."""
    hex_ip, _, hex_port = addr.partition(":")
    ip = _hex_to_ipv6(hex_ip) if is_v6 else _hex_to_ipv4(hex_ip)
    return ip, int(hex_port, 16)


def _read_tcp_file(path: str, is_v6: bool) -> list[SocketEntry]:
    entries: list[SocketEntry] = []
    try:
        with open(path) as f:
            next(f, None)  # skip header
            for line in f:
                parts = line.split()
                if len(parts) < 10:
                    continue
                try:
                    lip, lport = _parse_addr(parts[1], is_v6)
                    rip, rport = _parse_addr(parts[2], is_v6)
                    entries.append(
                        SocketEntry(
                            protocol="tcp6" if is_v6 else "tcp",
                            local_ip=lip,
                            local_port=lport,
                            remote_ip=rip,
                            remote_port=rport,
                            state=TCP_STATES.get(parts[3], parts[3]),
                            uid=int(parts[7]),
                            inode=parts[9],
                        )
                    )
                except (ValueError, IndexError):
                    continue
    except (OSError, PermissionError):
        pass
    return entries


def collect_sockets() -> list[SocketEntry]:
    """Collect all TCP sockets from /proc/net/tcp and /proc/net/tcp6."""
    return _read_tcp_file("/proc/net/tcp", False) + _read_tcp_file(
        "/proc/net/tcp6", True
    )


def listening_ports() -> list[int]:
    """Return sorted unique local ports in LISTEN state."""
    return sorted({s.local_port for s in collect_sockets() if s.state == "LISTEN"})
