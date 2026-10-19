"""Detection engine: rule registry and per-event evaluation."""

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol


log = logging.getLogger("siem.detect")


@dataclass
class Alert:
    """A detection result to be persisted."""
    rule_id: str
    severity: str
    title: str
    details: dict[str, Any]


class Rule(Protocol):
    """Interface every detection rule implements."""

    id: str
    severity: str
    title: str

    def evaluate(
        self, event: dict, agent_id: str, context: "RuleContext"
    ) -> Alert | None:
        """Return an Alert if the event triggers, else None."""
        ...


@dataclass
class RuleContext:
    """Mutable per-agent state shared across rule evaluations.

    For Day 6 this lives only in process memory. Later it'll be backed by
    Redis so multiple backend replicas share state. Keys are
    (rule_id, agent_id, *extra) tuples.
    """
    state: dict[tuple, Any] = field(default_factory=dict)

    def get(self, key: tuple, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set(self, key: tuple, value: Any) -> None:
        self.state[key] = value


RULES: list[Rule] = []


def register(rule: Rule) -> Rule:
    """Register a rule so it evaluates on every event."""
    RULES.append(rule)
    log.info("registered rule: %s (%s)", rule.id, rule.severity)
    return rule


def _agent_context(agent_id: str) -> RuleContext:
    """Retrieve or create the RuleContext for an agent."""
    if not hasattr(_agent_context, "contexts"):
        _agent_context.contexts = {}  # type: ignore[attr-defined]
    contexts = _agent_context.contexts  # type: ignore[attr-defined]
    if agent_id not in contexts:
        contexts[agent_id] = RuleContext()
    return contexts[agent_id]


def evaluate_event(
    event: dict, agent_id: str, context: RuleContext | None = None
) -> list[Alert]:
    """Run every registered rule against an event, return all fired alerts."""
    ctx = context or _agent_context(agent_id)
    alerts: list[Alert] = []
    for rule in RULES:
        try:
            alert = rule.evaluate(event, agent_id, ctx)
            if alert is not None:
                alerts.append(alert)
        except Exception as exc:
            log.exception("rule %s failed: %s", rule.id, exc)
    return alerts
