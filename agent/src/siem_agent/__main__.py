"""Entrypoint: run the agent and print metrics every N seconds."""

import json
import time

from siem_agent.metrics import get_system_metrics


def main() -> None:
    """Run the agent collection loop (stdout for Day 1)."""
    print("Cloud-Native SIEM Agent starting...")
    while True:
        metrics = get_system_metrics()
        print(json.dumps(metrics.to_dict()))
        time.sleep(10)


if __name__ == "__main__":
    main()
