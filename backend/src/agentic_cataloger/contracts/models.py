"""Shared agent-run vocabulary (framework-free): stage kinds and result shape."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal


class StageKind(StrEnum):
    """Closed set of in-scope pipeline stages."""

    DISCOVER_CREATE = "discover_create"
    ASSIGN = "assign"


@dataclass(frozen=True, slots=True)
class StageResult:
    """Outcome of one stage attempt, keyed by the LangGraph run it belongs to.

    ``run_id`` is caller-supplied, in LangGraph's own terminology — we reuse
    LangGraph's ``run_id``/``attempt`` vocabulary rather than inventing
    ``stage_execution_id``/``stage_attempt_id``; it does not mean LangGraph
    mints the id itself. The caller mints a UUIDv7 per product and passes
    it as both ``RunnableConfig["run_id"]`` (``uuid.UUID | None``) and graph
    state; note the type difference from this field, which is ``str``.
    ``attempt`` mirrors LangGraph's own ``node_attempt``, read from
    ``runtime.execution_info.node_attempt`` (LangGraph 1.2+) inside a node —
    not synthesized here.
    """

    run_id: str
    stage: StageKind
    attempt: int
    status: Literal["success", "defer", "invalid"]
    payload: Mapping[str, object] | None = None
    reason: str | None = None
