"""Built-in detection rules."""

import re
import time
from collections import deque

from siem_backend.detections.engine import Alert, RuleContext, register


FAILURE_PATTERNS = [
    re.compile(r"Failed password", re.IGNORECASE),
    re.compile(r"authentication failure", re.IGNORECASE),
    re.compile(r"Invalid user", re.IGNORECASE),
    re.compile(r"PAM authentication failure", re.IGNORECASE),
]


def _looks_like_failure(line: str) -> bool:
    return any(p.search(line) for p in FAILURE_PATTERNS)


class FailedAuthSpike:
    """Fire when N auth failures occur for an agent in a sliding window."""

    id = "auth_fail_spike"
    severity = "high"
    title = "Repeated authentication failures"

    window_seconds: int = 300
    threshold: int = 5
    cooldown_seconds: int = 60

    def evaluate(
        self, event: dict, agent_id: str, context: RuleContext
    ) -> Alert | None:
        if event.get("type") != "auth":
            return None
        line = event.get("line", "")
        if not _looks_like_failure(line):
            return None
        return self._track(agent_id, context, line)

    def _track(
        self, agent_id: str, context: RuleContext, line: str
    ) -> Alert | None:
        now = time.time()
        key = (self.id, agent_id)
        state = context.get(key) or {"window": deque(), "last_alert": 0.0}
        window: deque = state["window"]

        window.append(now)
        cutoff = now - self.window_seconds
        while window and window[0] < cutoff:
            window.popleft()

        context.set(key, state)

        if len(window) < self.threshold:
            return None
        if now - state["last_alert"] < self.cooldown_seconds:
            return None

        state["last_alert"] = now
        context.set(key, state)

        return Alert(
            rule_id=self.id,
            severity=self.severity,
            title=self.title,
            details={
                "count": len(window),
                "window_seconds": self.window_seconds,
                "threshold": self.threshold,
                "sample_line": line[:200],
            },
        )


_rule = FailedAuthSpike()
register(_rule)


class NewListeningPort:
    """Fire when a port not in the agent's baseline starts listening.

    First-ever run for an agent establishes the baseline silently.
    Subsequent new ports trigger an alert.
    """

    id = "new_listening_port"
    severity = "medium"
    title = "New listening port detected"

    def evaluate(
        self, event: dict, agent_id: str, context: RuleContext
    ) -> Alert | None:
        if event.get("type") != "port_opened":
            return None
        try:
            port = int(event.get("port"))
        except (TypeError, ValueError):
            return None

        key = (self.id, agent_id)
        baseline: set[int] = context.get(key) or set()

        if not baseline:
            baseline.add(port)
            context.set(key, baseline)
            return None

        if port in baseline:
            return None

        baseline.add(port)
        context.set(key, baseline)

        return Alert(
            rule_id=self.id,
            severity=self.severity,
            title=self.title,
            details={
                "port": port,
                "baseline_ports": sorted(baseline),
            },
        )


_new_port_rule = NewListeningPort()
register(_new_port_rule)


class HighCpuSustained:
    """Fire when CPU stays above threshold for N consecutive metric cycles."""

    id = "high_cpu_sustained"
    severity = "medium"
    title = "Sustained high CPU usage"

    threshold: float = 85.0
    min_consecutive: int = 3
    cooldown_seconds: int = 300

    def evaluate(
        self, event: dict, agent_id: str, context: RuleContext
    ) -> Alert | None:
        if event.get("type") != "metrics":
            return None
        try:
            cpu = float(event.get("cpu_percent", 0.0))
        except (TypeError, ValueError):
            return None

        now = time.time()
        key = (self.id, agent_id)
        state = context.get(key) or {"consecutive": 0, "last_alert": 0.0}

        if cpu < self.threshold:
            state["consecutive"] = 0
            context.set(key, state)
            return None

        state["consecutive"] += 1
        context.set(key, state)

        if state["consecutive"] < self.min_consecutive:
            return None
        if now - state["last_alert"] < self.cooldown_seconds:
            return None

        state["last_alert"] = now
        context.set(key, state)

        return Alert(
            rule_id=self.id,
            severity=self.severity,
            title=self.title,
            details={
                "consecutive": state["consecutive"],
                "cpu_percent": cpu,
                "threshold": self.threshold,
            },
        )


_high_cpu_rule = HighCpuSustained()
register(_high_cpu_rule)


class PortScan:
    """Fire when an agent reports many new listening ports rapidly."""

    id = "port_scan"
    severity = "high"
    title = "Rapid port opening detected"

    window_seconds: int = 30
    threshold: int = 10
    cooldown_seconds: int = 300

    def evaluate(
        self, event: dict, agent_id: str, context: RuleContext
    ) -> Alert | None:
        if event.get("type") != "port_opened":
            return None
        
        now = time.time()
        key = (self.id, agent_id)
        state = context.get(key) or {"window": deque(), "last_alert": 0.0}
        window: deque = state["window"]

        window.append(now)
        cutoff = now - self.window_seconds
        while window and window[0] < cutoff:
            window.popleft()

        context.set(key, state)

        if len(window) < self.threshold:
            return None
        if now - state["last_alert"] < self.cooldown_seconds:
            return None

        state["last_alert"] = now
        context.set(key, state)

        return Alert(
            rule_id=self.id,
            severity=self.severity,
            title=self.title,
            details={
                "count": len(window),
                "window_seconds": self.window_seconds,
            },
        )


register(PortScan())


class UnusualOutbound:
    """Fire when a connection is established to a public (non-private) IP."""

    id = "unusual_outbound"
    severity = "medium"
    title = "Outbound connection to public IP"

    def evaluate(
        self, event: dict, agent_id: str, context: RuleContext
    ) -> Alert | None:
        if event.get("type") != "connection":
            return None
        if event.get("state") != "ESTABLISHED":
            return None

        rip = event.get("remote_ip", "")
        if not rip:
            return None
            
        # Simple check for private/local IPs
        if rip.startswith(("127.", "10.", "192.168.", "0.0.0.0", "::1")):
            return None
        if rip.startswith("172."):
            try:
                second_octet = int(rip.split(".")[1])
                if 16 <= second_octet <= 31:
                    return None
            except (IndexError, ValueError):
                pass

        return Alert(
            rule_id=self.id,
            severity=self.severity,
            title=self.title,
            details={"remote_ip": rip, "remote_port": event.get("remote_port")},
        )


register(UnusualOutbound())
