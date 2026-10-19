"""Tests for detection rules."""

from siem_backend.detections.engine import RuleContext, evaluate_event
from siem_backend.detections import rules  # noqa: F401 - self-registers


def test_auth_fail_below_threshold():
    ctx = RuleContext()
    line = {"type": "auth", "line": "sshd: Failed password for root"}
    for _ in range(4):
        assert evaluate_event(line, "a1", ctx) == []


def test_auth_fail_fires_at_threshold():
    ctx = RuleContext()
    line = {"type": "auth", "line": "sshd: Failed password for root"}
    for _ in range(4):
        evaluate_event(line, "a1", ctx)
    alerts = evaluate_event(line, "a1", ctx)
    assert len(alerts) == 1
    assert alerts[0].rule_id == "auth_fail_spike"
    assert alerts[0].severity == "high"
    assert alerts[0].details["count"] == 5


def test_auth_fail_cooldown_suppresses():
    ctx = RuleContext()
    line = {"type": "auth", "line": "sshd: Failed password for root"}
    for _ in range(5):
        evaluate_event(line, "a1", ctx)
    # 6th within cooldown should not fire
    assert evaluate_event(line, "a1", ctx) == []


def test_auth_fail_ignores_success():
    ctx = RuleContext()
    ok = {"type": "auth", "line": "Accepted publickey for user"}
    for _ in range(10):
        assert evaluate_event(ok, "a1", ctx) == []


def test_auth_fail_per_agent_isolation():
    ctx = RuleContext()
    line = {"type": "auth", "line": "Failed password"}
    for _ in range(5):
        evaluate_event(line, "a1", ctx)
    # a2 starts fresh
    assert evaluate_event(line, "a2", ctx) == []


def test_new_port_baselines_silently():
    ctx = RuleContext()
    evt = {"type": "port_opened", "port": 8022}
    assert evaluate_event(evt, "b1", ctx) == []


def test_new_port_fires_when_not_in_baseline():
    ctx = RuleContext()
    evaluate_event({"type": "port_opened", "port": 8022}, "b1", ctx)
    alerts = evaluate_event({"type": "port_opened", "port": 8765}, "b1", ctx)
    assert len(alerts) == 1
    assert alerts[0].rule_id == "new_listening_port"
    assert alerts[0].details["port"] == 8765


def test_new_port_repeat_no_alert():
    ctx = RuleContext()
    evaluate_event({"type": "port_opened", "port": 8022}, "b1", ctx)
    evaluate_event({"type": "port_opened", "port": 8765}, "b1", ctx)
    assert evaluate_event({"type": "port_opened", "port": 8022}, "b1", ctx) == []


def test_cpu_below_threshold_no_alert():
    ctx = RuleContext()
    evt = {"type": "metrics", "cpu_percent": 20}
    for _ in range(10):
        assert evaluate_event(evt, "c1", ctx) == []


def test_cpu_sustained_fires():
    ctx = RuleContext()
    evt = {"type": "metrics", "cpu_percent": 95}
    assert evaluate_event(evt, "c1", ctx) == []
    assert evaluate_event(evt, "c1", ctx) == []
    alerts = evaluate_event(evt, "c1", ctx)
    assert len(alerts) == 1
    assert alerts[0].rule_id == "high_cpu_sustained"
    assert alerts[0].details["consecutive"] == 3


def test_cpu_resets_on_dip():
    ctx = RuleContext()
    hi = {"type": "metrics", "cpu_percent": 95}
    lo = {"type": "metrics", "cpu_percent": 20}
    evaluate_event(hi, "c1", ctx)
    evaluate_event(hi, "c1", ctx)
    evaluate_event(lo, "c1", ctx)  # reset
    assert evaluate_event(hi, "c1", ctx) == []  # back to count=1


def test_cpu_cooldown_after_fire():
    ctx = RuleContext()
    evt = {"type": "metrics", "cpu_percent": 95}
    for _ in range(3):
        evaluate_event(evt, "c1", ctx)
    # 4th high immediately: cooldown active
    assert evaluate_event(evt, "c1", ctx) == []
