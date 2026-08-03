"""Worker role: blocking stub until SIGTERM (advisory lock lands in Story 1.3)."""

from __future__ import annotations

import logging
import signal
import time

logger = logging.getLogger(__name__)


def run_worker() -> None:
    """Run the worker stub until SIGTERM or SIGINT.

    Raises:
        SystemExit: Always exits ``0`` after a clean shutdown signal.
    """
    is_stopping = False

    def _handle_sigterm(_signum: int, _frame: object | None) -> None:
        """Mark the worker loop for clean shutdown."""
        nonlocal is_stopping
        is_stopping = True

    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    logger.info("agentic-cataloger worker started (stub — no queue consumer yet)")
    while not is_stopping:
        time.sleep(1)
    logger.info("agentic-cataloger worker shutting down")
    raise SystemExit(0)


if __name__ == "__main__":
    run_worker()
