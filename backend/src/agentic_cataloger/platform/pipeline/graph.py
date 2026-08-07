"""Per-product LangGraph StateGraph: ``assign`` and ``defer`` nodes (Phase 2).

Phase 3 adds a real ``discover_create`` node between them. Until then, any
miss the domain's pure ``route_after_assign`` would send to
``"discover_create"`` is routed straight to ``"defer"`` in this module's
``path_map`` — there's nowhere else for it to go yet. The domain routing
rule itself already distinguishes the two outcomes; only this module's
edge wiring collapses them for now.

Compiled without a checkpointer: no resume path exists yet, and the
``langgraph`` schema created at migrate time is deliberately unused until
durable stage outcomes / replay (roadmap 4.2) lands.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import RetryPolicy

from agentic_cataloger.platform.pipeline.nodes import (
    RunState,
    StageDeps,
    assign_node,
    defer_node,
    route_after_assign,
)

ASSIGN_RETRY_POLICY = RetryPolicy(max_attempts=3)


def build_stage_graph() -> CompiledStateGraph[Any, Any, Any, Any]:
    """Compile the per-product stage graph.

    Returns:
        Compiled graph: ``assign`` -> END on a clean assign, -> ``defer``
        on any miss (Phase 2; Phase 3 splits the miss path so a first miss
        reaches a real ``discover_create`` node instead).
    """
    builder = StateGraph(RunState, context_schema=StageDeps)
    builder.add_node("assign", assign_node, retry_policy=ASSIGN_RETRY_POLICY)
    builder.add_node("defer", defer_node)
    builder.add_edge("__start__", "assign")
    builder.add_conditional_edges(
        "assign",
        route_after_assign,
        {END: END, "discover_create": "defer", "defer": "defer"},
    )
    builder.add_edge("defer", END)
    return builder.compile()


__all__ = ["build_stage_graph"]
