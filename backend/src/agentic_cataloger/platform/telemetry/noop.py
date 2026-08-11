"""No-op telemetry adapter (export disabled)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import final

from agentic_cataloger.pipeline.ports import AttributeValue, SpanHandle, Telemetry


@final
class NoOpSpanHandle(SpanHandle):
    """Span handle that discards all operations."""

    def set_attribute(self, key: str, value: AttributeValue) -> None:
        """Discard the attribute."""
        _ = (self, key, value)

    def set_status(self, *, ok: bool, description: str = "") -> None:
        """Discard the status."""
        _ = (self, ok, description)

    def end(self) -> None:
        """No-op end."""
        _ = self


@final
class NoOpTelemetry(Telemetry):
    """Telemetry that never exports; safe when the collector env is unset."""

    def start_span(
        self,
        name: str,
        *,
        attributes: Mapping[str, AttributeValue] | None = None,
    ) -> SpanHandle:
        """Return a discard handle.

        Returns:
            A no-op span handle.
        """
        _ = (self, name, attributes)
        return NoOpSpanHandle()

    def current_trace_id(self) -> str | None:
        """Always ``None`` — nothing is being traced.

        Returns:
            ``None``.
        """
        _ = self
        return None

    def shutdown(self) -> None:
        """No-op — nothing to flush or release."""
        _ = self
