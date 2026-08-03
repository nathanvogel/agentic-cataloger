"""Wire CSV latest-file ingest to the catalog import command."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from pricecomp.catalog.commands import (
    CSV_ADAPTER_VERSION,
    ImportSnapshotRequest,
    import_snapshot,
)
from pricecomp.catalog.ingest_filter import IngestFilter
from pricecomp.catalog.models import ImportSnapshotResult
from pricecomp.platform.ingest.csv_source import (
    RETAILERS,
    find_latest_csv,
    iter_retailer_dirs,
    parse_csv_snapshot,
)
from pricecomp.platform.persistence.catalog_repo import (
    PsycopgProductRepository,
    PsycopgSnapshotRepository,
    PsycopgUnitOfWork,
    connect_app,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IngestRunSummary:
    """Aggregate result of one ``pricecomp ingest`` invocation."""

    results: tuple[ImportSnapshotResult, ...]

    @property
    def snapshot_count(self) -> int:
        """Number of retailer snapshots processed."""
        return len(self.results)

    @property
    def upserted_count(self) -> int:
        """Total products upserted across snapshots."""
        return sum(item.upserted_count for item in self.results)

    @property
    def deferred_count(self) -> int:
        """Total deferred (no-product) rows across snapshots."""
        return sum(item.deferred_count for item in self.results)

    @property
    def collision_count(self) -> int:
        """Total intra-snapshot identity collisions across snapshots."""
        return sum(item.collision_count for item in self.results)

    @property
    def matched_count(self) -> int:
        """Total observations that matched the ingest filter."""
        return sum(item.matched_count for item in self.results)

    @property
    def filtered_out_count(self) -> int:
        """Total unique observations dropped by the ingest filter."""
        return sum(item.filtered_out_count for item in self.results)


def run_ingest(
    *,
    data_dir: Path,
    database_url: str | None = None,
    retailers: tuple[str, ...] | None = None,
    ingest_filter: IngestFilter | None = None,
) -> IngestRunSummary:
    """Import the latest CSV per selected retailer into the catalog.

    Args:
        data_dir: Root ``data/`` directory containing ``*-ch-products`` folders.
        database_url: App DB URL; defaults to ``DATABASE_URL``.
        retailers: Optional subset of ``migros`` / ``lidl`` / ``coop`` / ``denner``.
        ingest_filter: Optional product filter (source category / keyword).
            Empty = bulk.

    Returns:
        Aggregate ingest summary.

    Raises:
        RuntimeError: If ``DATABASE_URL`` is unset.
        ValueError: If a requested retailer is unknown or has no CSV.
    """
    active_filter = ingest_filter if ingest_filter is not None else IngestFilter()
    url = (database_url or os.environ.get("DATABASE_URL", "")).strip()
    if not url:
        msg = "DATABASE_URL must be set for ingest"
        raise RuntimeError(msg)

    selected = retailers if retailers is not None else RETAILERS
    unknown = sorted(set(selected) - set(RETAILERS))
    if unknown:
        msg = f"Unknown retailer(s): {unknown}"
        raise ValueError(msg)

    wanted = set(selected)
    results: list[ImportSnapshotResult] = []

    with connect_app(url) as conn:
        snapshots = PsycopgSnapshotRepository(conn)
        products = PsycopgProductRepository(conn)
        uow = PsycopgUnitOfWork(conn)

        for retailer, retailer_dir in iter_retailer_dirs(data_dir):
            if retailer not in wanted:
                continue
            latest = find_latest_csv(retailer_dir)
            if latest is None:
                msg = f"No CSV snapshots found under {retailer_dir}"
                raise ValueError(msg)
            parsed = parse_csv_snapshot(
                retailer=retailer,
                path=latest,
                data_dir=data_dir,
                retailer_dir=retailer_dir,
            )
            logger.info(
                "Importing %s (%s) — %d rows, %d deferred candidates",
                parsed.relative_path,
                parsed.source_namespace,
                len(parsed.observations) + len(parsed.deferred),
                len(parsed.deferred),
            )
            result = import_snapshot(
                ImportSnapshotRequest(
                    source_namespace=parsed.source_namespace,
                    source_observed_at=parsed.source_observed_at,
                    content_checksum=parsed.content_checksum,
                    source_path=parsed.relative_path,
                    observations=parsed.observations,
                    deferred=parsed.deferred,
                    adapter_version=CSV_ADAPTER_VERSION,
                    ingest_filter=active_filter,
                ),
                snapshots=snapshots,
                products=products,
                uow=uow,
            )
            results.append(result)
            logger.info(
                "Snapshot %s new=%s upserted=%d matched=%d filtered_out=%d "
                "deferred=%d collisions=%d",
                result.snapshot.id,
                result.is_new_snapshot,
                result.upserted_count,
                result.matched_count,
                result.filtered_out_count,
                result.deferred_count,
                result.collision_count,
            )

    imported_retailers = {
        result.snapshot.source_namespace.removesuffix("-ch") for result in results
    }
    still_missing = wanted - imported_retailers
    if still_missing:
        msg = f"No data imported for retailer(s): {sorted(still_missing)}"
        raise ValueError(msg)

    return IngestRunSummary(results=tuple(results))
