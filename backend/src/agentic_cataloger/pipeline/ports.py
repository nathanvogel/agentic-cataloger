"""Application ports for pipeline / telemetry."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from agentic_cataloger.catalog.ingest_filter import IngestFilter
from agentic_cataloger.pipeline.models import RunProductRef

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


class RunProductRepository(Protocol):
    """Read path for selecting a set of catalog products for a pipeline run."""

    def list_for_run(
        self,
        *,
        ingest_filter: IngestFilter,
        unassigned_only: bool,
        limit: int | None,
    ) -> Sequence[RunProductRef]:
        """Return products matching ``ingest_filter``.

        Args:
            ingest_filter: Category/keyword criteria (empty = no filtering).
            unassigned_only: Exclude products with an existing taxonomy leaf
                membership when True.
            limit: Optional row cap; None means no limit.
        """
        ...
