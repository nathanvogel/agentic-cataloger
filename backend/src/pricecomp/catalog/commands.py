"""Import a catalog snapshot and upsert products under durable source identity."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid7

from pricecomp.catalog.errors import (
    IdentityPolicyConflictError,
    SourceIdentityCollisionError,
    UntrustedSourceIdentityError,
)
from pricecomp.catalog.identity import IDENTITY_POLICY_VERSION, SourceIdentity
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
    now: datetime | None = None


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
    adapter_version = request.adapter_version

    existing_policy = products.get_identity_policy_version(request.source_namespace)
    if existing_policy is not None and existing_policy != identity_policy_version:
        raise IdentityPolicyConflictError(
            f"Namespace {request.source_namespace!r} already imported under policy "
            f"{existing_policy!r}; refusing {identity_policy_version!r} without "
            "a migration/alias map"
        )

    existing = snapshots.get_by_checksum_and_adapter(
        content_checksum=request.content_checksum,
        adapter_version=adapter_version,
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
            adapter_version=adapter_version,
            source_path=request.source_path,
        )
        snapshots.insert(snapshot)

    by_identity: dict[SourceIdentity, list[ProductObservation]] = defaultdict(list)
    for observation in request.observations:
        by_identity[observation.identity].append(observation)

    colliding: list[SourceIdentity] = []
    unique_observations: list[ProductObservation] = []
    for identity, group in by_identity.items():
        if len(group) > 1:
            colliding.append(identity)
            logger.warning(
                "Intra-snapshot identity collision for %s (%d rows); skipping",
                identity,
                len(group),
            )
            continue
        unique_observations.append(group[0])

    upserted = 0
    for observation in unique_observations:
        existing_product = products.get_by_source_identity(observation.identity)
        product_id = existing_product.id if existing_product is not None else uuid7()
        products.upsert_observation(
            product_id=product_id,
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
    )


def assert_no_collisions(result: ImportSnapshotResult) -> None:
    """Raise when an import reported intra-snapshot identity collisions.

    Args:
        result: Import outcome.

    Raises:
        SourceIdentityCollisionError: If any colliding identities were skipped.
    """
    if result.collision_count:
        raise SourceIdentityCollisionError(
            f"{result.collision_count} intra-snapshot identity collision(s)"
        )


__all__ = [
    "CSV_ADAPTER_VERSION",
    "ImportSnapshotRequest",
    "UntrustedSourceIdentityError",
    "assert_no_collisions",
    "import_snapshot",
]
