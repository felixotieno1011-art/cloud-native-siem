"""Auth log collection for Termux/Android.

Termux does not run sshd by default and has no /var/log/auth.log.
We scan a configurable list of candidate paths and tail new lines.
On plain Android, `logcat` is the fallback via subprocess if available.
"""

import os
from dataclasses import dataclass, asdict
from typing import Any


DEFAULT_PATHS = [
    os.path.expandvars("$PREFIX/var/log/auth.log"),
    os.path.expandvars("$PREFIX/var/log/sshd.log"),
    "/var/log/auth.log",
]


@dataclass
class AuthEvent:
    """A single auth log line."""
    source: str
    line: str
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AuthLogTailer:
    """Tails auth logs, remembering file offsets between calls."""

    def __init__(self, paths: list[str] | None = None) -> None:
        self.paths = paths or DEFAULT_PATHS
        self._offsets: dict[str, int] = {}

    def tail(self) -> list[AuthEvent]:
        """Read new lines from all existing log files."""
        import time

        events: list[AuthEvent] = []
        for path in self.paths:
            if not os.path.isfile(path):
                continue
            try:
                size = os.path.getsize(path)
                offset = self._offsets.get(path, size)  # start at end on first call
                if size < offset:
                    offset = 0
                with open(path) as f:
                    f.seek(offset)
                    for raw in f:
                        line = raw.rstrip("\n")
                        if line:
                            events.append(
                                AuthEvent(source=path, line=line, timestamp=time.time())
                            )
                    self._offsets[path] = f.tell()
            except OSError:
                continue
        return events
