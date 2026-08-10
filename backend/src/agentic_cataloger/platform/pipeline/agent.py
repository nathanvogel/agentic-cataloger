"""LangChain-backed StageAgent: model + bound tools + structured output.

Along with ``tools.py``, this is the only module allowed to import
``langchain``/``langgraph`` in the pipeline vertical — mirrors
``platform/taxonomy/tools.py``'s role for the taxonomy vertical.

Owns the three loop guards from the design discussion's resolved
"tool-calling agent loop" decision:

- **Loop length** — ``recursion_limit`` passed at invoke time;
  ``GraphRecursionError`` is caught here and turned into
  ``action="defer"`` rather than escaping as a traceback.
- **Tool-call budget** — ``ToolCallLimitMiddleware`` refuses further tool
  calls past a fixed budget and forces the model to answer with what it
  has (``exit_behavior="continue"``).
- **Wall clock / spend** — ``chat_model()``'s ``timeout=``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any, Literal, cast
from uuid import UUID

import psycopg
from langchain.agents import create_agent
from langchain.agents.middleware.tool_call_limit import ToolCallLimitMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel

from agentic_cataloger.catalog.models import CatalogProductRef
from agentic_cataloger.pipeline.models import (
    AssignDecision,
    CreateDecision,
    DeferDecision,
    RejectedCandidate,
    StageDecision,
)
from agentic_cataloger.platform.llm.openrouter import chat_model
from agentic_cataloger.platform.pipeline.prompts import (
    ASSIGN_SYSTEM_PROMPT,
    DISCOVER_SYSTEM_PROMPT,
)
from agentic_cataloger.platform.pipeline.tools import (
    build_assign_tools,
    build_discover_tools,
)

logger = logging.getLogger(__name__)

# Refuse further tool calls past this many in one decide() call — forces
# the model to answer (assign or defer) with what it already has.
TOOL_CALL_BUDGET = 8
# LangGraph step budget for the inner agent loop. Each model/tool cycle
# costs ~3 steps (model → tool → middleware)
RECURSION_LIMIT = 10


class _AssignDecisionSchema(BaseModel):
    """Structured output schema for the assign stage.

    Converted to the domain ``StageDecision`` by
    ``_assign_decision_from_schema`` — the assign stage can never emit
    ``action="create"`` because this schema doesn't offer it.
    """

    action: Literal["assign", "defer"]
    leaf_id: str | None = None
    reason: str | None = None


def _assign_decision_from_schema(schema: BaseModel) -> StageDecision:
    """Convert the assign stage's structured response into a StageDecision.

    Args:
        schema: Parsed ``_AssignDecisionSchema`` instance.

    Returns:
        Domain decision; an unparseable ``leaf_id`` is treated as absent
        (the node then routes it like any other miss).
    """
    # to_decision is only ever wired to the matching response_schema at
    # construction time (build_assign_stage_agent pairs the two) — cast
    # rather than assert/isinstance since this is a static, not runtime, fact.
    parsed = cast(_AssignDecisionSchema, schema)
    if parsed.action == "defer":
        return DeferDecision(reason=parsed.reason)
    leaf_id: UUID | None = None
    if parsed.leaf_id:
        try:
            leaf_id = UUID(parsed.leaf_id)
        except ValueError:
            logger.warning(
                "Assign stage returned an unparseable leaf_id=%r", parsed.leaf_id
            )
    if leaf_id is not None:
        return AssignDecision(leaf_id=leaf_id, reason=parsed.reason)
    return DeferDecision(
        reason=parsed.reason or "assign response missing leaf_id",
    )


def _render_product(product: CatalogProductRef, context: Mapping[str, object]) -> str:
    """Render one product (plus optional extra context) as the user turn.

    Args:
        product: Product this stage attempt is deciding about.
        context: Extra prompt context (e.g. a discover-created candidate
            leaf in Phase 3); empty on a first pass.

    Returns:
        Plain-text product description for the agent's first message.
    """
    lines = [
        f"product_id: {product.product_id}",
        f"name: {product.name}",
    ]
    if product.name_de:
        lines.append(f"name_de: {product.name_de}")
    if product.source_category:
        lines.append(
            "source_category (retailer label, not authoritative): "
            f"{product.source_category}"
        )
    if product.unified_category:
        lines.append(
            "unified_category (retailer label, not authoritative): "
            f"{product.unified_category}"
        )
    for key, value in context.items():
        lines.append(f"{key}: {value}")
    return "\n".join(lines)


class LangChainStageAgent:
    """One stage's tool-calling loop over a bound chat model.

    Tools, prompt, and response schema are all stage-specific and fixed at
    construction time; ``decide`` only varies by the product (and optional
    context) it's deciding about.
    """

    def __init__(  # ruff: ignore[too-many-arguments]
        self,
        *,
        tools: list[BaseTool],
        system_prompt: str,
        response_schema: type[BaseModel],
        to_decision: Callable[[BaseModel], StageDecision],
        model: BaseChatModel | None = None,
        recursion_limit: int = RECURSION_LIMIT,
        tool_call_budget: int = TOOL_CALL_BUDGET,
    ) -> None:
        """Build one stage's compiled agent.

        Args:
            tools: Tools bound for this stage only (disjoint per stage).
            system_prompt: Rubric + task framing for this stage.
            response_schema: Pydantic schema for ``response_format``.
            to_decision: Converts a parsed ``response_schema`` instance
                into the domain ``StageDecision``.
            model: Chat model; defaults to ``chat_model()``.
            recursion_limit: Passed to the agent's own ``invoke`` call.
            tool_call_budget: Max tool calls per ``decide()`` before the
                model is forced to answer with what it has.
        """
        super().__init__()
        self._agent = create_agent(
            model=model if model is not None else chat_model(),
            tools=tools,
            system_prompt=system_prompt,
            response_format=response_schema,
            middleware=[
                ToolCallLimitMiddleware(
                    run_limit=tool_call_budget, exit_behavior="continue"
                ),
            ],
        )
        self._to_decision = to_decision
        self._recursion_limit = recursion_limit

    def decide(
        self,
        *,
        product: CatalogProductRef,
        context: Mapping[str, object],
    ) -> StageDecision:
        """Run this stage's agent loop for one product.

        Args:
            product: Product this stage attempt is deciding about.
            context: Extra prompt context; empty on a first pass.

        Returns:
            The stage's decision. A ``GraphRecursionError`` or an absent
            structured response both convert to ``action="defer"`` rather
            than escaping as a traceback.
        """
        try:
            outcome = self._agent.invoke(
                {"messages": [HumanMessage(content=_render_product(product, context))]},
                config={"recursion_limit": self._recursion_limit},
            )
        except GraphRecursionError as exc:
            logger.warning(
                "Stage hit recursion_limit=%d for product_id=%s: %s",
                self._recursion_limit,
                product.product_id,
                exc,
            )
            return DeferDecision(reason=f"recursion limit exceeded: {exc}")

        structured = outcome.get("structured_response")
        if structured is None:
            logger.warning(
                "Stage produced no structured response for product_id=%s",
                product.product_id,
            )
            return DeferDecision(reason="model returned no structured response")
        return self._to_decision(structured)


def build_assign_stage_agent(conn: psycopg.Connection[Any]) -> LangChainStageAgent:
    """Build the assign stage's agent, with tools bound to ``conn``.

    Args:
        conn: Live psycopg connection for this product's stages.

    Returns:
        Configured agent for the assign stage.
    """
    return LangChainStageAgent(
        tools=build_assign_tools(conn),
        system_prompt=ASSIGN_SYSTEM_PROMPT,
        response_schema=_AssignDecisionSchema,
        to_decision=_assign_decision_from_schema,
    )


# ---------------------------------------------------------------------------
# Discover/create stage
# ---------------------------------------------------------------------------


class _RejectedCandidateSchema(BaseModel):
    """One category the discover stage considered and rejected."""

    category_id: str
    name: str


class _DiscoverDecisionSchema(BaseModel):
    """Structured output schema for the discover stage.

    Converted to the domain ``StageDecision`` by
    ``_discover_decision_from_schema``.  The discover stage can never emit
    ``action="assign"`` because this schema doesn't offer it.
    """

    action: Literal["create", "defer"]
    parent_id: str | None = None
    names: list[str] = []
    rejected: list[_RejectedCandidateSchema] = []
    reason: str | None = None


def _discover_decision_from_schema(schema: BaseModel) -> StageDecision:
    """Convert the discover stage's structured response into a StageDecision.

    Args:
        schema: Parsed ``_DiscoverDecisionSchema`` instance.

    Returns:
        Domain decision; an unparseable ``parent_id`` is treated as absent.
    """
    parsed = cast(_DiscoverDecisionSchema, schema)
    if parsed.action == "defer":
        return DeferDecision(reason=parsed.reason)

    parent_id: UUID | None = None
    if parsed.parent_id:
        try:
            parent_id = UUID(parsed.parent_id)
        except ValueError:
            logger.warning(
                "Discover stage returned an unparseable parent_id=%r", parsed.parent_id
            )

    rejected: tuple[RejectedCandidate, ...] = ()
    valid_rejected: list[RejectedCandidate] = []
    for r in parsed.rejected:
        if not r.category_id:
            continue
        try:
            valid_rejected.append(
                RejectedCandidate(category_id=UUID(r.category_id), name=r.name)
            )
        except ValueError:
            logger.warning(
                "Discover stage returned unparseable rejected category_id=%r",
                r.category_id,
            )
    rejected = tuple(valid_rejected)

    if parent_id is None:
        return DeferDecision(
            reason=parsed.reason or "create response missing parent_id",
        )

    return CreateDecision(
        parent_id=parent_id,
        names=tuple(parsed.names),
        rejected=rejected,
        reason=parsed.reason,
    )


def build_discover_stage_agent(conn: psycopg.Connection[Any]) -> LangChainStageAgent:
    """Build the discover stage's agent, with tools bound to ``conn``.

    Args:
        conn: Live psycopg connection for this product's stages.

    Returns:
        Configured agent for the discover/create stage.
    """
    return LangChainStageAgent(
        tools=build_discover_tools(conn),
        system_prompt=DISCOVER_SYSTEM_PROMPT,
        response_schema=_DiscoverDecisionSchema,
        to_decision=_discover_decision_from_schema,
    )


__all__ = [
    "LangChainStageAgent",
    "build_assign_stage_agent",
    "build_discover_stage_agent",
]
