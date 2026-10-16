"""Tests for auth log tailing."""

import os
import tempfile

from siem_agent.authlog import AuthLogTailer


def test_tailer_reads_new_lines_only():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("initial line\n")
        path = f.name
    try:
        tailer = AuthLogTailer(paths=[path])
        assert tailer.tail() == []  # first call seeks to EOF

        with open(path, "a") as f:
            f.write("new line 1\nnew line 2\n")

        events = tailer.tail()
        assert len(events) == 2
        assert events[0].line == "new line 1"
        assert events[1].line == "new line 2"
    finally:
        os.unlink(path)
