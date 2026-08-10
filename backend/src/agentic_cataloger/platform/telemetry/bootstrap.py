"""Telemetry bootstrap — ``phoenix.otel.register`` or no-op."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Final

from agentic_cataloger.pipeline.ports import Telemetry
from agentic_cataloger.platform.telemetry.noop import NoOpTelemetry
from agentic_cataloger.platform.telemetry.phoenix_adapter import PhoenixTelemetry

logger = logging.getLogger(__name__)

_DEFAULT_PROJECT: Final = "agentic-cataloger"
_TRACER_NAME: Final = "agentic_cataloger"
_TRACES_PATH: Final = "/v1/traces"


@dataclass
class _TelemetryState:
    """Process-wide telemetry holder (avoids bare ``global``)."""

    active: Telemetry | None = field(default=None)


_state = _TelemetryState()


def otlp_http_traces_endpoint(collector_base: str) -> str:
    """Return the OTLP HTTP traces URL for a Phoenix collector base URL.

    Args:
        collector_base: Phoenix UI / collector base (e.g. ``http://phoenix:6006``)
            or an already-qualified ``.../v1/traces`` URL.

    Returns:
        Endpoint ending in ``/v1/traces``.
    """
    base = collector_base.strip().rstrip("/")
    if base.endswith(_TRACES_PATH):
        return base
    return f"{base}{_TRACES_PATH}"


def configure_telemetry() -> Telemetry:
    """Return Phoenix-backed telemetry when the collector endpoint is set.

    When ``PHOENIX_COLLECTOR_ENDPOINT`` is unset, returns ``NoOpTelemetry`` and
    never calls ``phoenix.otel.register`` (avoids its localhost:6006 default).

    Returns:
        A process-wide ``Telemetry`` implementation.
    """
    if _state.active is not None:
        return _state.active

    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "").strip()
    if not endpoint:
        logger.info(
            "PHOENIX_COLLECTOR_ENDPOINT unset; telemetry export disabled (NoOp)",
        )
        _state.active = NoOpTelemetry()
        return _state.active

    project = (
        os.environ.get("PHOENIX_PROJECT_NAME")
        or os.environ.get("PHOENIX_PROJECT")
        or _DEFAULT_PROJECT
    )
    traces_endpoint = otlp_http_traces_endpoint(endpoint)
    from phoenix.otel import register

    logger.info(
        "Configuring Phoenix telemetry project=%s endpoint=%s",
        project,
        traces_endpoint,
    )
    provider = register(
        project_name=project,
        endpoint=traces_endpoint,
        protocol="http/protobuf",
        batch=False,
        # Wires openinference-instrumentation-langchain so pipeline stage
        # LLM calls (create_agent's ChatOpenAI) get their own OpenInference
        # spans automatically under the product LangGraph tree. This is a
        # *global* flag (patches
        # langchain_core.callbacks.BaseCallbackManager.__init__), so it also
        # starts auto-instrumenting complete_openrouter's ChatOpenAI call
        # (telemetry smoke) — that path now emits both the hand-rolled leaf
        # LLM span (record_leaf_llm_span) and an auto-instrumented one.
        # Accepted for now (roadmap 4.6 is where cost-join double-counting
        # would actually bite); the pipeline spans are the ones that matter.
        auto_instrument=True,
    )
    tracer = provider.get_tracer(_TRACER_NAME)
    _state.active = PhoenixTelemetry(tracer, provider)
    return _state.active


def shutdown_telemetry() -> None:
    """Flush and shut down the active telemetry adapter, if any."""
    if _state.active is None:
        return
    try:
        _state.active.shutdown()
    except Exception:
        logger.exception("Failed to shut down telemetry")
    _state.active = None


def reset_telemetry_for_tests() -> None:
    """Clear the process-wide telemetry singleton (tests only)."""
    _state.active = None
