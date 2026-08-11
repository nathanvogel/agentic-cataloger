"""App-role PostgreSQL connections via a process-wide pool.

A ``psycopg.Connection`` is **not safe for concurrent use** (not even for
read-only queries). Two threads sharing one connection race on the wire
protocol and the session's single active transaction. Concurrent work —
including LangGraph ``ToolNode`` fan-out of parallel tool calls — must
borrow a **separate** connection per concurrent task.

Pattern (same as a typical HTTP request handler):

1. Process holds a ``ConnectionPool`` (see ``get_app_pool``).
2. Each unit of work does ``with connect_app(url) as conn:`` (or
   ``with pool.connection() as conn:``).
3. That block owns ``conn`` exclusively until exit; the pool resets and
   returns it for reuse.

Do not close over one ``Connection`` in tools or workers that may run in
parallel. Hold a pool (or URL) and check out inside each call instead.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Final, cast

import psycopg
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool

# Enough for one stage's parallel tool fan-out (tool-call budget is 8) plus
# a few concurrent node/runner checkouts without blocking.
DEFAULT_POOL_MAX_SIZE: Final = 16
DEFAULT_POOL_MIN_SIZE: Final = 1

_pools: dict[str, ConnectionPool[Any]] = {}
_pools_lock = threading.Lock()


def get_app_pool(
    database_url: str,
    *,
    max_size: int = DEFAULT_POOL_MAX_SIZE,
    min_size: int = DEFAULT_POOL_MIN_SIZE,
) -> ConnectionPool[Any]:
    """Return the process-wide pool for ``database_url``, creating it if needed.

    Args:
        database_url: ``postgresql://…`` URL for ``agentic_cataloger_app``.
        max_size: Cap on open connections in this pool.
        min_size: Connections kept warm when idle.

    Returns:
        Open ``ConnectionPool``. Callers that need exclusive use must still
        check out via ``pool.connection()`` or ``connect_app`` — never share
        one borrowed connection across threads.
    """
    with _pools_lock:
        pool = _pools.get(database_url)
        if pool is not None and not pool.closed:
            return pool
        created: ConnectionPool[Any] = ConnectionPool(
            conninfo=database_url,
            min_size=min_size,
            max_size=max_size,
            kwargs={
                "row_factory": cast(Any, dict_row),
                "autocommit": False,
            },
            open=True,
            name="agentic_cataloger_app",
        )
        _pools[database_url] = created
        return created


def close_app_pools() -> None:
    """Close and forget every process-wide app pool.

    Call before dropping test databases or process shutdown so idle pooled
    connections do not block ``DROP DATABASE``.
    """
    with _pools_lock:
        for pool in _pools.values():
            if not pool.closed:
                pool.close()
        _pools.clear()


@contextmanager
def connect_app(database_url: str) -> Iterator[psycopg.Connection[DictRow]]:
    """Borrow one exclusive app connection from the process pool.

    The yielded connection must not be used concurrently. For parallel tool
    calls or threads, open a separate ``connect_app`` / ``pool.connection``
    block in each task.

    Args:
        database_url: ``postgresql://…`` URL for ``agentic_cataloger_app``.

    Yields:
        A connection with dict rows and ``autocommit=False``. On exit the
        pool resets it (rollback) and returns it for reuse.
    """
    pool = get_app_pool(database_url)
    with pool.connection() as conn:
        yield cast(psycopg.Connection[DictRow], conn)


__all__ = [
    "DEFAULT_POOL_MAX_SIZE",
    "DEFAULT_POOL_MIN_SIZE",
    "close_app_pools",
    "connect_app",
    "get_app_pool",
]
