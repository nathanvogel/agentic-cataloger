"""Per-product LangGraph StateGraph: assign, discover, and defer nodes.

Graph shape:

    __start__ → assign
    assign → END       (clean assign)
    assign → discover  (miss with discover budget remaining)
    assign → defer     (miss after discover budget exhausted)
    discover → assign  (created a leaf, re-prompt assign fresh)
    discover → defer   (invalid proposal, cap exceeded, or model defer)
    defer → END

Both ``assign`` and ``discover`` carry ``RetryPolicy(max_attempts=3)``
so a flaky LLM call retries at the node level before escalating to defer.

Compiled without a checkpointer (no resume path yet).
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
        Compiled graph with the full assign → discover → assign
        loop and ping-pong guard (``discover_count`` in state caps discover
        at three iterations per product).
    """
    builder = StateGraph(RunState, context_schema=StageDeps)

    builder.add_node("assign", assign_node, retry_policy=ASSIGN_RETRY_POLICY)
    builder.add_node("discover", discover_node, retry_policy=DISCOVER_RETRY_POLICY)
    builder.add_node("defer", defer_node)

    builder.add_edge("__start__", "assign")

    builder.add_conditional_edges("assign", route_after_assign)
    builder.add_conditional_edges("discover", route_after_discover)
    builder.add_edge("defer", END)

    return builder.compile()


__all__ = ["build_stage_graph"]
