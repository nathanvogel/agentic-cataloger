"""Import a catalog snapshot and upsert products under durable source identity."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid7

from pricecomp.catalog.errors import IdentityPolicyConflictError
from pricecomp.catalog.identity import IDENTITY_POLICY_VERSION, SourceIdentity
from pricecomp.catalog.ingest_filter import IngestFilter
from pricecomp.catalog.models import (
    CatalogSnapshot,
    ImportSnapshotResult,
    ProductObservation,
)
from pricecomp.catalog.ports import (
    CatalogUnitOfWork,
    ProductRepository,
    SnapshotRepository,
)
from pricecomp.catalog.timeutil import ensure_utc

logger = logging.getLogger(__name__)

# Adapter version for the Yelinz HuggingFace CSV layout (latest-file ingest).
CSV_ADAPTER_VERSION = "yelinz-csv@1"


@dataclass(frozen=True, slots=True)
class ImportSnapshotRequest:
    """Inputs for registering one snapshot and upserting its products."""

    source_namespace: str
    source_observed_at: datetime
    content_checksum: str
    source_path: str
    observations: Sequence[ProductObservation]
    deferred: Sequence[tuple[str, str]]
    adapter_version: str = CSV_ADAPTER_VERSION
    identity_policy_version: str = IDENTITY_POLICY_VERSION
    ingest_filter: IngestFilter = field(default_factory=IngestFilter)
    now: datetime | None = None


def _partition_unique_observations(
    observations: Sequence[ProductObservation],
) -> tuple[list[ProductObservation], list[SourceIdentity]]:
    """Split observations into unique rows vs colliding identities.

    Returns:
        Unique observations (one per identity) and the colliding identities.
    """
    by_identity: dict[SourceIdentity, list[ProductObservation]] = defaultdict(list)
    for observation in observations:
        by_identity[observation.identity].append(observation)

    colliding: list[SourceIdentity] = []
    unique: list[ProductObservation] = []
    for identity, group in by_identity.items():
        if len(group) > 1:
            colliding.append(identity)
            logger.warning(
                "Intra-snapshot identity collision for %s (%d rows); skipping",
                identity,
                len(group),
            )
            continue
        unique.append(group[0])
    return unique, colliding


def _apply_ingest_filter(
    ingest_filter: IngestFilter,
    unique_observations: Sequence[ProductObservation],
    *,
    source_path: str,
) -> tuple[list[ProductObservation], int]:
    """Apply ingest filter; warn when a non-empty filter matches nothing.

    Returns:
        Matching observations and how many unique rows were filtered out.
    """
    matched = ingest_filter.filter_observations(unique_observations)
    filtered_out_count = len(unique_observations) - len(matched)
    if not ingest_filter.is_empty and not matched:
        logger.warning(
            "Ingest filter matched 0 of %d unique observations "
            "(source_category=%r keyword=%r) for %s",
            len(unique_observations),
            ingest_filter.source_category,
            ingest_filter.keyword,
            source_path,
        )
    return matched, filtered_out_count


def import_snapshot(
    request: ImportSnapshotRequest,
    *,
    snapshots: SnapshotRepository,
    products: ProductRepository,
    uow: CatalogUnitOfWork,
) -> ImportSnapshotResult:
    """Register an immutable snapshot and upsert its trustworthy products.

    Re-registering the same checksum + adapter version reuses the existing
    snapshot row (idempotent). Products upsert on source identity. Rows without
    a trustworthy ID must be passed via ``deferred`` and produce no product row.
    Intra-snapshot identity collisions are reported and skipped (not upserted).
    ``ingest_filter`` narrows which unique observations upsert (empty = bulk).

    Args:
        request: Snapshot metadata plus observations / deferred rows.
        snapshots: Snapshot repository port.
        products: Product repository port.
        uow: Unit of work for one transactional write.

    Returns:
        Import outcome including upsert / defer / collision counts.

    Raises:
        IdentityPolicyConflictError: Namespace already used a different policy.
    """
    observed_at = ensure_utc(request.source_observed_at)
    clock = request.now if request.now is not None else datetime.now(UTC)
    identity_policy_version = request.identity_policy_version

    existing_policy = products.get_identity_policy_version(request.source_namespace)
    if existing_policy is not None and existing_policy != identity_policy_version:
        raise IdentityPolicyConflictError(
            f"Namespace {request.source_namespace!r} already imported under policy "
            f"{existing_policy!r}; refusing {identity_policy_version!r} without "
            "a migration/alias map"
        )

    existing = snapshots.get_by_checksum_and_adapter(
        content_checksum=request.content_checksum,
        adapter_version=request.adapter_version,
    )
    is_new_snapshot = existing is None
    if existing is not None:
        snapshot = existing
    else:
        snapshot = CatalogSnapshot(
            id=uuid7(),
            source_namespace=request.source_namespace,
            source_observed_at=observed_at,
            content_checksum=request.content_checksum,
            adapter_version=request.adapter_version,
            source_path=request.source_path,
        )
        snapshots.insert(snapshot)

    unique_observations, colliding = _partition_unique_observations(
        request.observations
    )
    matched, filtered_out_count = _apply_ingest_filter(
        request.ingest_filter,
        unique_observations,
        source_path=request.source_path,
    )

    upserted = 0
    for observation in matched:
        # Always mint a UUIDv7; ON CONFLICT keeps the existing row id.
        products.upsert_observation(
            product_id=uuid7(),
            observation=observation,
            snapshot_id=snapshot.id,
            identity_policy_version=identity_policy_version,
            now=clock,
        )
        upserted += 1

    uow.commit()

    deferred_urls = tuple(url for url, _reason in request.deferred)
    return ImportSnapshotResult(
        snapshot=snapshot,
        is_new_snapshot=is_new_snapshot,
        upserted_count=upserted,
        deferred_count=len(request.deferred),
        collision_count=len(colliding),
        deferred_urls=deferred_urls,
        colliding_identities=tuple(colliding),
        matched_count=len(matched),
        filtered_out_count=filtered_out_count,
    )


__all__ = [
    "CSV_ADAPTER_VERSION",
    "ImportSnapshotRequest",
    "import_snapshot",
]
