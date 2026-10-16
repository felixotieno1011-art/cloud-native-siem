"""Tests for /proc/net/tcp parsing."""

from siem_agent.ports import _hex_to_ipv4, _parse_addr, collect_sockets


def test_hex_to_ipv4_localhost():
    # 0100007F little-endian -> 127.0.0.1
    assert _hex_to_ipv4("0100007F") == "127.0.0.1"


def test_parse_addr_ipv4():
    ip, port = _parse_addr("0100007F:1F90", False)
    assert ip == "127.0.0.1"
    assert port == 8080


def test_collect_sockets_returns_list():
    result = collect_sockets()
    assert isinstance(result, list)
    for entry in result:
        assert entry.protocol in ("tcp", "tcp6")
        assert 0 <= entry.local_port <= 65535
