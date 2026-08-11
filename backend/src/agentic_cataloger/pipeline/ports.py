"""Application ports for pipeline / telemetry."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from agentic_cataloger.catalog.models import CatalogProductRef
from agentic_cataloger.pipeline.models import StageDecision

AttributeValue = str | int | float | bool


class SpanHandle(Protocol):
    """Opaque handle for a started span (string-keyed attributes only)."""

    def set_attribute(self, key: str, value: AttributeValue) -> None:
        """Set a single attribute on this span."""
        ...

    def set_status(self, *, ok: bool, description: str = "") -> None:
        """Set the span status (OK vs ERROR) shown in Phoenix.

        Args:
            ok: True for OK, False for ERROR.
            description: Optional status message (usually on ERROR).
        """
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


class StageAgent(Protocol):
    """One separately-prompted stage. The adapter owns the model and tools.

    Production wiring supplies a LangChain-backed implementation; tests
    supply a fake returning canned ``StageDecision``s.
    """

    def decide(
        self,
        *,
        product: CatalogProductRef,
        context: Mapping[str, object],
    ) -> StageDecision:
        """Decide this stage's outcome for one product.

        Args:
            product: The product this stage attempt is working on.
            context: Extra context for the prompt (e.g. a candidate leaf a
                prior stage created); empty on a first pass.
        """
        ...
