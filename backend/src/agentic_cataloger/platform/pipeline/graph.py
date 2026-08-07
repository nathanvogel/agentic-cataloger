"""Per-product LangGraph StateGraph: assign, discover_create, and defer nodes.

Graph shape (from the design discussion diagram):

    __start__ → assign
    assign → END              (clean assign)
    assign → discover_create  (first miss, discover not yet run)
    assign → defer            (second miss, discover already ran)
    discover_create → assign  (created a leaf, re-prompt assign fresh)
    discover_create → defer   (invalid proposal, cap exceeded, or model defer)
    defer → END

Both ``assign`` and ``discover_create`` carry ``RetryPolicy(max_attempts=3)``
so a flaky LLM call retries at the node level before escalating to defer.

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
    discover_node,
    route_after_assign,
    route_after_discover,
)

ASSIGN_RETRY_POLICY = RetryPolicy(max_attempts=3)
DISCOVER_RETRY_POLICY = RetryPolicy(max_attempts=3)


def build_stage_graph() -> CompiledStateGraph[Any, Any, Any, Any]:
    """Compile the per-product stage graph.

    Returns:
        Compiled graph with the full assign → discover_create → assign
        loop and ping-pong guard (``discover_ran`` in state ensures
        discover fires at most once per product).
    """
    builder = StateGraph(RunState, context_schema=StageDeps)

    builder.add_node("assign", assign_node, retry_policy=ASSIGN_RETRY_POLICY)
    builder.add_node(
        "discover_create", discover_node, retry_policy=DISCOVER_RETRY_POLICY
    )
    builder.add_node("defer", defer_node)

    builder.add_edge("__start__", "assign")

    builder.add_conditional_edges(
        "assign",
        route_after_assign,
        {END: END, "discover_create": "discover_create", "defer": "defer"},
    )
    builder.add_conditional_edges(
        "discover_create",
        route_after_discover,
        {"assign": "assign", "defer": "defer"},
    )
    builder.add_edge("defer", END)

    return builder.compile()


__all__ = ["build_stage_graph"]
