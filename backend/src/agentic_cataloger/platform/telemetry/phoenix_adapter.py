"""Phoenix-backed Telemetry adapter (OpenTelemetry tracer wrapper)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast, final

from opentelemetry import context, trace
from opentelemetry.util.types import AttributeValue as OtelAttributeValue

from agentic_cataloger.pipeline.ports import AttributeValue, SpanHandle, Telemetry


@final
class PhoenixSpanHandle(SpanHandle):
    """SpanHandle over an OpenTelemetry span attached to the current context."""

    def __init__(self, span: Any, token: object) -> None:
        """Bind to ``span`` and the context ``token`` from ``context.attach``.

        Args:
            span: Live OpenTelemetry span (or Phoenix ``OITracer`` span).
            token: Token returned by ``context.attach`` for later detach.
        """
        super().__init__()
        self._span = span
        self._token = token
        self._ended = False

    def set_attribute(self, key: str, value: AttributeValue) -> None:
        """Set an attribute on the underlying span."""
        self._span.set_attribute(key, cast(OtelAttributeValue, value))

    def end(self) -> None:
        """End the span and detach its context."""
        if self._ended:
            return
        self._ended = True
        self._span.end()
        context.detach(self._token)  # type: ignore[arg-type]


@final
class PhoenixTelemetry(Telemetry):
    """Telemetry port implemented with a Phoenix-registered tracer."""

    def __init__(self, tracer: Any, provider: Any | None = None) -> None:
        """Wrap ``tracer``; optional ``provider`` is shut down by bootstrap.

        Args:
            tracer: Tracer from ``phoenix.otel.register(...).get_tracer(...)``
                (may be OpenInference ``OITracer``).
            provider: Tracer provider returned by ``register``, if owned here.
        """
        super().__init__()
        self._tracer = tracer
        self._provider = provider

    def start_span(
        self,
        name: str,
        *,
        attributes: Mapping[str, AttributeValue] | None = None,
    ) -> SpanHandle:
        """Start a span and attach it as the current span.

        Returns:
            A handle that ends the span and detaches context.
        """
        span = self._tracer.start_span(name)
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        ctx_token = context.attach(trace.set_span_in_context(span))
        return PhoenixSpanHandle(span, ctx_token)

    def current_trace_id(self) -> str | None:
        """Return the active trace id as 32-char lowercase hex, or ``None``.

        Returns:
            Lowercase hex trace id, or ``None`` when no valid span is current.
        """
        _ = self
        span = trace.get_current_span()
        span_context = span.get_span_context()
        if not span_context.is_valid:
            return None
        return format(span_context.trace_id, "032x")

    def shutdown(self) -> None:
        """Force-flush and shut down the owned tracer provider, if any."""
        if self._provider is None:
            return
        self._provider.force_flush()
        self._provider.shutdown()
        self._provider = None
