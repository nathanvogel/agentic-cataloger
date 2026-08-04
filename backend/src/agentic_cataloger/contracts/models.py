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

    ``run_id`` is reused as-is from LangGraph's own run identifier (e.g.
    ``RunnableConfig.run_id``) — no synthetic per-stage-execution or
    per-attempt ID is minted here. ``attempt`` is a plain retry counter,
    mirroring LangGraph's own ``node_attempt``.
    """

    run_id: str
    stage: StageKind
    attempt: int
    status: Literal["success", "defer", "invalid"]
    payload: Mapping[str, object] | None = None
    reason: str | None = None
