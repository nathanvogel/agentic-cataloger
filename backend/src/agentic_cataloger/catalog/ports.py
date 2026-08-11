"""Application ports for catalog persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from agentic_cataloger.catalog.identity import SourceIdentity
from agentic_cataloger.catalog.ingest_filter import IngestFilter
from agentic_cataloger.catalog.models import (
    CatalogProduct,
    CatalogProductRef,
    CatalogSnapshot,
    ProductObservation,
)


class CatalogUnitOfWork(Protocol):
    """One transactional boundary for catalog writes."""

    def commit(self) -> None:
        """Commit the unit of work."""
        ...

    def rollback(self) -> None:
        """Roll back the unit of work."""
        ...


class SnapshotRepository(Protocol):
    """Persistence for immutable catalog snapshots."""

    def get_by_checksum_and_adapter(
        self,
        *,
        content_checksum: str,
        adapter_version: str,
    ) -> CatalogSnapshot | None:
        """Return an existing snapshot for checksum + adapter version, if any."""
        ...

    def insert(self, snapshot: CatalogSnapshot) -> CatalogSnapshot:
        """Insert a new snapshot row."""
        ...


class ProductRepository(Protocol):
    """Persistence for catalog products keyed by source identity."""

    def get_by_source_identity(self, identity: SourceIdentity) -> CatalogProduct | None:
        """Return the product for a source identity, if present."""
        ...

    def get_identity_policy_version(self, source_namespace: str) -> str | None:
        """Return the identity policy version already used in a namespace, if any."""
        ...

    def upsert_observation(
        self,
        *,
        product_id: UUID,
        observation: ProductObservation,
        snapshot_id: UUID,
        identity_policy_version: str,
        now: datetime,
    ) -> CatalogProduct:
        """Insert or update mutable observations; never touch enrichment state."""
        ...


class CatalogProductQuery(Protocol):
    """Read path for filtered slim catalog product refs."""

    def list_refs(
        self,
        *,
        ingest_filter: IngestFilter,
        unassigned_only: bool,
        limit: int | None,
    ) -> Sequence[CatalogProductRef]:
        """Return products matching ``ingest_filter``.

        Args:
            ingest_filter: Category/keyword criteria (empty = no filtering).
            unassigned_only: Exclude products with an existing taxonomy leaf
                membership when True.
            limit: Optional row cap; None means no limit.
        """
        ...
