"""Tests for metrics collection."""

from siem_agent.metrics import get_system_metrics


def test_get_system_metrics_returns_valid_snapshot():
    metrics = get_system_metrics()
    assert metrics.hostname
    assert 0 <= metrics.cpu_percent <= 100
    assert 0 <= metrics.memory_percent <= 100
    assert 0 <= metrics.disk_percent <= 100
    assert metrics.load_avg_1m >= 0
    assert metrics.timestamp > 0
