"""Worker role: blocking stub until SIGTERM (advisory lock lands in Story 1.3)."""

from __future__ import annotations

import signal
import time


def run_worker() -> None:
    """Run the worker stub until SIGTERM or SIGINT.

    Raises:
        SystemExit: Always exits `0` after a clean shutdown signal.
    """
    stop = False

    def _handle_sigterm(_signum: int, _frame: object | None) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    print("pricecomp worker started (stub — no queue consumer yet)", flush=True)
    while not stop:
        time.sleep(1)
    print("pricecomp worker shutting down", flush=True)
    raise SystemExit(0)


if __name__ == "__main__":
    run_worker()
