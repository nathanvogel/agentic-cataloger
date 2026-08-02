"""Throwaway GATE-03 work-state + PgQueuer helpers (not catalog domain)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Literal

import psycopg
from pgqueuer import PgQueuer
from pgqueuer.adapters.drivers.psycopg import PsycopgDriver
from pgqueuer.adapters.persistence import qb
from pgqueuer.adapters.persistence.queries import Queries
from pgqueuer.domain.models import Channel
from pgqueuer.domain.settings import DBSettings
from pgqueuer.domain.types import QueueExecutionMode
from pgqueuer.ports.tracing import TracingProtocol

PGQUEUER_SCHEMA = "pgqueuer"
ENTRYPOINT = "gate03_reliance"
WORK_STATES = (
    "pending",
    "running",
    "retry_wait",
    "completed",
    "failed",
    "cancelled",
)
WorkState = Literal[
    "pending",
    "running",
    "retry_wait",
    "completed",
    "failed",
    "cancelled",
]

# AD-22 central retry policy (P8 asserts these; tests may use shorter delays)
MAX_INFRA_ATTEMPTS = 5
RETRY_CAP = timedelta(minutes=15)
TERMINAL_STATES = frozenset({"completed", "failed", "cancelled"})

CREATE_WORK_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS gate03_work (
    id UUID PRIMARY KEY,
    pipeline_run_id UUID NOT NULL,
    state TEXT NOT NULL
        CHECK (state IN ('pending','running','retry_wait','completed','failed','cancelled')),
    effect_count INT NOT NULL DEFAULT 0,
    attempt_count INT NOT NULL DEFAULT 0,
    cancel_requested BOOLEAN NOT NULL DEFAULT FALSE,
    disposition TEXT,
    milestone TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


@dataclass(frozen=True)
class WorkRow:
    id: uuid.UUID
    pipeline_run_id: uuid.UUID
    state: str
    effect_count: int
    attempt_count: int
    cancel_requested: bool
    disposition: str | None
    milestone: str | None
    payload: dict[str, Any]


def ensure_work_table(migrate_url: str) -> None:
    with psycopg.connect(migrate_url, autocommit=True) as conn:
        conn.execute(CREATE_WORK_TABLE_SQL)
        conn.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON gate03_work TO pricecomp_app")


def truncate_work_table(migrate_url: str) -> None:
    with psycopg.connect(migrate_url, autocommit=True) as conn:
        conn.execute("TRUNCATE TABLE gate03_work")


def _row_from(record: tuple[Any, ...]) -> WorkRow:
    return WorkRow(
        id=record[0],
        pipeline_run_id=record[1],
        state=record[2],
        effect_count=record[3],
        attempt_count=record[4],
        cancel_requested=record[5],
        disposition=record[6],
        milestone=record[7],
        payload=record[8] if isinstance(record[8], dict) else json.loads(record[8] or "{}"),
    )


def insert_work(
    dsn: str,
    *,
    work_id: uuid.UUID | None = None,
    pipeline_run_id: uuid.UUID | None = None,
    state: WorkState = "pending",
    disposition: str | None = None,
    payload: dict[str, Any] | None = None,
) -> WorkRow:
    work_id = work_id or uuid.uuid4()
    pipeline_run_id = pipeline_run_id or uuid.uuid4()
    with psycopg.connect(dsn, autocommit=False) as conn:
        conn.execute(
            """
            INSERT INTO gate03_work (
                id, pipeline_run_id, state, disposition, payload
            ) VALUES (%s, %s, %s, %s, %s::jsonb)
            """,
            (
                work_id,
                pipeline_run_id,
                state,
                disposition,
                json.dumps(payload or {}),
            ),
        )
        conn.commit()
    row = get_work(dsn, work_id)
    assert row is not None
    return row


def get_work(dsn: str, work_id: uuid.UUID) -> WorkRow | None:
    with psycopg.connect(dsn, autocommit=True) as conn:
        record = conn.execute(
            """
            SELECT id, pipeline_run_id, state, effect_count, attempt_count,
                   cancel_requested, disposition, milestone, payload
            FROM gate03_work WHERE id = %s
            """,
            (work_id,),
        ).fetchone()
    return _row_from(record) if record else None


def update_work(
    dsn: str,
    work_id: uuid.UUID,
    *,
    state: WorkState | None = None,
    effect_count: int | None = None,
    attempt_count: int | None = None,
    cancel_requested: bool | None = None,
    disposition: str | None = None,
    milestone: str | None = None,
    set_disposition: bool = False,
) -> WorkRow:
    sets: list[str] = ["updated_at = now()"]
    params: list[Any] = []
    if state is not None:
        sets.append("state = %s")
        params.append(state)
    if effect_count is not None:
        sets.append("effect_count = %s")
        params.append(effect_count)
    if attempt_count is not None:
        sets.append("attempt_count = %s")
        params.append(attempt_count)
    if cancel_requested is not None:
        sets.append("cancel_requested = %s")
        params.append(cancel_requested)
    if set_disposition or disposition is not None:
        sets.append("disposition = %s")
        params.append(disposition)
    if milestone is not None:
        sets.append("milestone = %s")
        params.append(milestone)
    params.append(work_id)
    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute(
            f"UPDATE gate03_work SET {', '.join(sets)} WHERE id = %s",
            params,
        )
    row = get_work(dsn, work_id)
    assert row is not None
    return row


def build_queries(
    driver: PsycopgDriver,
    *,
    tracer: TracingProtocol | None = None,
) -> Queries:
    settings = DBSettings(db_schema=PGQUEUER_SCHEMA)
    qbe = qb.QueryBuilderEnvironment(settings=settings)
    qbq = qb.QueryQueueBuilder(settings=settings)
    qbs = qb.QuerySchedulerBuilder(settings=settings)
    return Queries(driver, qbe=qbe, qbq=qbq, qbs=qbs, tracer=tracer)


async def open_queue(
    dsn: str,
    *,
    tracer: TracingProtocol | None = None,
) -> tuple[psycopg.AsyncConnection, PgQueuer, Queries]:
    conn = await psycopg.AsyncConnection.connect(dsn, autocommit=True)
    # PgQueuer Job.headers BeforeValidator calls from_json(); psycopg returns
    # JSONB as dict by default — keep jsonb/json as text for the driver path.
    from psycopg.types.string import TextLoader

    conn.adapters.register_loader("jsonb", TextLoader)
    conn.adapters.register_loader("json", TextLoader)
    driver = PsycopgDriver(conn)
    settings = DBSettings(db_schema=PGQUEUER_SCHEMA)
    queries = build_queries(driver, tracer=tracer)
    pgq = PgQueuer(
        connection=driver,
        channel=Channel(settings.channel),
        queries=queries,
    )
    if tracer is not None:
        pgq.qm.tracer = tracer
    return conn, pgq, queries


def clear_queue(migrate_url: str) -> None:
    with psycopg.connect(migrate_url, autocommit=True) as conn:
        conn.execute("DELETE FROM pgqueuer.pgqueuer")
        conn.execute("DELETE FROM pgqueuer.pgqueuer_log")


async def enqueue_after_commit(
    dsn: str,
    work_id: uuid.UUID,
    *,
    tracer: TracingProtocol | None = None,
    headers: dict[str, Any] | None = None,
) -> list:
    """Commit owner row first, then enqueue — never in the same transaction."""
    # Owner row is assumed already committed by the caller.
    conn, _pgq, queries = await open_queue(dsn, tracer=tracer)
    try:
        return await queries.enqueue(
            ENTRYPOINT,
            str(work_id).encode(),
            headers=headers,
        )
    finally:
        await conn.close()


async def redrive_from_owner_row(
    dsn: str,
    work_id: uuid.UUID,
    *,
    tracer: TracingProtocol | None = None,
) -> list | None:
    """Re-enqueue when owner row is non-terminal (lost-enqueue recovery)."""
    row = get_work(dsn, work_id)
    if row is None or row.state in TERMINAL_STATES:
        return None
    return await enqueue_after_commit(dsn, work_id, tracer=tracer)


def langgraph_conn_string(base_url: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}options=-c%20search_path%3Dlanggraph"


async def drain_once(
    pgq: PgQueuer,
    *,
    batch_size: int = 1,
    heartbeat_timeout: timedelta = timedelta(seconds=30),
) -> None:
    await pgq.run(
        dequeue_timeout=timedelta(seconds=0.2),
        batch_size=batch_size,
        mode=QueueExecutionMode.drain,
        max_concurrent_tasks=max(2, batch_size * 2),
        heartbeat_timeout=heartbeat_timeout,
        log_aggregation_interval=timedelta(0),
    )
