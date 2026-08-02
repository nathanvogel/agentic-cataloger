"""Subprocess worker for GATE-03 P4 SIGKILL mid-handler proof."""

from __future__ import annotations

import asyncio
import os
import sys


async def _amain() -> None:
    dsn = os.environ["DATABASE_URL"]
    migrate_url = os.environ.get("MIGRATE_DATABASE_URL", dsn)
    sleep_s = float(os.environ.get("GATE03_SLEEP_AFTER_ENTER", "30"))

    from tests.integration.pgqueuer_reliance_handlers import register_handlers
    from tests.integration.pgqueuer_reliance_helpers import open_queue

    conn, pgq, _queries = await open_queue(dsn)
    try:
        register_handlers(
            pgq,
            dsn=dsn,
            migrate_url=migrate_url,
            sleep_after_enter=sleep_s,
        )
        # Continuous until killed; use short heartbeat so a restart can reclaim.
        from datetime import timedelta

        from pgqueuer.domain.types import QueueExecutionMode

        await pgq.run(
            dequeue_timeout=timedelta(seconds=0.5),
            batch_size=1,
            mode=QueueExecutionMode.continuous,
            max_concurrent_tasks=2,
            heartbeat_timeout=timedelta(seconds=2),
            log_aggregation_interval=timedelta(0),
        )
    finally:
        await conn.close()


def main() -> None:
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        raise SystemExit(0) from None


if __name__ == "__main__":
    # Ensure backend root is importable when spawned as a script.
    from pathlib import Path

    backend_root = Path(__file__).resolve().parents[2]
    src = backend_root / "src"
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    main()
