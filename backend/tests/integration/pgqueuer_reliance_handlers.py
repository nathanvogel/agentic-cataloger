"""Idempotent GATE-03 job handlers (throwaway; not production catalog dispatch)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta
from typing import Any

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from pgqueuer.core.executors import DatabaseRetryEntrypointExecutor
from pgqueuer.domain.errors import RetryRequested
from pgqueuer.domain.models import Context, Job
from typing_extensions import TypedDict

from tests.integration.pgqueuer_reliance_helpers import (
    ENTRYPOINT,
    MAX_INFRA_ATTEMPTS,
    RETRY_CAP,
    TERMINAL_STATES,
    WorkRow,
    get_work,
    langgraph_conn_string,
    update_work,
)


class _GraphState(TypedDict):
    n: int
    effects: int


def _work_id_from_job(job: Job) -> uuid.UUID:
    return uuid.UUID(job.payload.decode() if job.payload else "")


def register_handlers(
    pgq: Any,
    *,
    dsn: str,
    migrate_url: str,
    sleep_after_enter: float = 0.0,
    force_infra_error: bool = False,
) -> None:
    """Register the GATE-03 entrypoint on *pgq*."""

    async def handle(job: Job, context: Context) -> None:
        del context  # cancellation is application-owned via cancel_requested
        work_id = _work_id_from_job(job)
        row = get_work(dsn, work_id)
        if row is None or row.state in TERMINAL_STATES:
            return

        if row.cancel_requested:
            update_work(dsn, work_id, state="cancelled", milestone="cancel_boundary")
            return

        disposition = row.disposition
        if disposition in {"invalid", "defer"}:
            # Deterministic outcomes never infrastructure-retry (AD-22).
            update_work(
                dsn,
                work_id,
                state="failed" if disposition == "invalid" else "completed",
                disposition=disposition,
                set_disposition=True,
                milestone="deterministic",
            )
            return

        force_infra = force_infra_error or bool((row.payload or {}).get("force_infra_error"))
        if force_infra:
            attempt = row.attempt_count + 1
            update_work(
                dsn,
                work_id,
                state="retry_wait",
                attempt_count=attempt,
                milestone="infra_fail",
            )
            if attempt >= MAX_INFRA_ATTEMPTS:
                update_work(dsn, work_id, state="failed", milestone="exhausted")
                raise RuntimeError("infra exhausted")
            delay = min(timedelta(milliseconds=50 * (2 ** (attempt - 1))), RETRY_CAP)
            raise RetryRequested(delay=delay, reason="simulated infra failure")

        if row.state == "pending":
            update_work(dsn, work_id, state="running", milestone="entered")

        if sleep_after_enter > 0:
            current = get_work(dsn, work_id)
            assert current is not None
            if current.milestone in {"entered", "parked"} or current.state == "running":
                update_work(dsn, work_id, milestone="parked")
                await asyncio.sleep(sleep_after_enter)

        # Safe boundary: re-check cancellation before side effects.
        row = get_work(dsn, work_id)
        assert row is not None
        if row.cancel_requested:
            update_work(dsn, work_id, state="cancelled", milestone="cancel_boundary")
            return

        await _apply_effect_and_complete(dsn, migrate_url, row)

    def retry_factory(params: Any) -> DatabaseRetryEntrypointExecutor:
        return DatabaseRetryEntrypointExecutor(
            parameters=params,
            max_attempts=MAX_INFRA_ATTEMPTS,
            initial_delay=timedelta(milliseconds=50),
            max_delay=timedelta(seconds=1),
        )

    pgq.entrypoint(
        ENTRYPOINT,
        on_failure="hold",
        accepts_context=True,
        executor_factory=retry_factory,
    )(handle)


async def _apply_effect_and_complete(
    dsn: str,
    migrate_url: str,
    row: WorkRow,
) -> None:
    """Idempotent effect: LangGraph resume on pipeline_run_id when requested."""
    if row.effect_count > 0:
        update_work(dsn, row.id, state="completed", milestone="done")
        return

    use_langgraph = bool((row.payload or {}).get("langgraph"))
    if use_langgraph:
        effects = await _run_langgraph(migrate_url, row)
    else:
        effects = 1

    update_work(
        dsn,
        row.id,
        state="completed",
        effect_count=row.effect_count + effects,
        milestone="done",
    )


async def _run_langgraph(migrate_url: str, row: WorkRow) -> int:
    """Resume AsyncPostgresSaver on thread_id=pipeline_run_id (P5)."""
    conn_string = langgraph_conn_string(migrate_url)
    config = {"configurable": {"thread_id": str(row.pipeline_run_id)}}

    def node_a(state: _GraphState) -> _GraphState:
        return {"n": state["n"] + 1, "effects": state["effects"] + 1}

    def node_b(state: _GraphState) -> _GraphState:
        return {"n": state["n"] + 10, "effects": state["effects"]}

    async with AsyncPostgresSaver.from_conn_string(conn_string) as saver:
        builder = StateGraph(_GraphState)
        builder.add_node("a", node_a)
        builder.add_node("b", node_b)
        builder.add_edge(START, "a")
        builder.add_edge("a", "b")
        builder.add_edge("b", END)
        graph = builder.compile(checkpointer=saver, interrupt_after=["a"])

        snapshot = await graph.aget_state(config)
        if snapshot.values:
            result = await graph.ainvoke(None, config)
        else:
            result = await graph.ainvoke({"n": 0, "effects": 0}, config)
            if not (row.payload or {}).get("langgraph_hold"):
                result = await graph.ainvoke(None, config)
        return int(result.get("effects", 0)) if isinstance(result, dict) else 0
