"""Application ports for pipeline / telemetry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

AttributeValue = str | int | float | bool


class SpanHandle(Protocol):
    """Opaque handle for a started span (string-keyed attributes only)."""

    def set_attribute(self, key: str, value: AttributeValue) -> None:
        """Set a single attribute on this span."""
        ...

    def end(self) -> None:
        """End this span."""
        ...


class Telemetry(Protocol):
    """Thin tracing port — no OpenTelemetry / Phoenix types leak here."""

    def start_span(
        self,
        name: str,
        *,
        attributes: Mapping[str, AttributeValue] | None = None,
    ) -> SpanHandle:
        """Start a span nested under the current span when one is active."""
        ...

    def current_trace_id(self) -> str | None:
        """Return the active trace id as lowercase hex, or ``None`` if idle."""
        ...

    def shutdown(self) -> None:
        """Flush and release exporter resources, if any."""
        ...
