"""Parse Yelinz retailer CSVs into catalog observations."""

from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from agentic_cataloger.catalog.errors import UntrustedSourceIdentityError
from agentic_cataloger.catalog.identity import (
    extract_source_identity,
    namespace_for_retailer,
)
from agentic_cataloger.catalog.models import ProductObservation

RETAILERS = ("migros", "lidl", "coop", "denner")
_SNAPSHOT_NAME = re.compile(
    r"^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})-"
    r"(?P<hour>\d{2}):(?P<minute>\d{2})\.csv$"
)


@dataclass(frozen=True, slots=True)
class ParsedCsvSnapshot:
    """One latest CSV file ready for catalog import."""

    retailer: str
    source_namespace: str
    path: Path
    relative_path: str
    source_observed_at: datetime
    content_checksum: str
    observations: tuple[ProductObservation, ...]
    deferred: tuple[tuple[str, str], ...]


def find_latest_csv(retailer_dir: Path) -> Path | None:
    """Return the latest ``YYYY/MM/DD-HH:MM.csv`` under a retailer folder.

    Args:
        retailer_dir: Path like ``data/migros-ch-products``.

    Returns:
        Absolute path to the newest snapshot file, or ``None`` if none exist.
    """
    if not retailer_dir.is_dir():
        return None
    candidates: list[tuple[datetime, Path]] = []
    for path in retailer_dir.rglob("*.csv"):
        rel = relative_under_retailer_dir(path, retailer_dir)
        observed = parse_snapshot_timestamp(rel)
        if observed is None:
            continue
        candidates.append((observed, path))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def relative_under_retailer_dir(path: Path, retailer_dir: Path) -> str:
    """Return ``YYYY/MM/DD-HH:MM.csv`` relative to a retailer folder.

    Args:
        path: Absolute CSV path.
        retailer_dir: Retailer root (``…/migros-ch-products``).

    Returns:
        POSIX relative path, or the file name if not under ``retailer_dir``.
    """
    try:
        return path.resolve().relative_to(retailer_dir.resolve()).as_posix()
    except ValueError:
        return path.name


def parse_snapshot_timestamp(relative_path: str) -> datetime | None:
    """Parse scrape time from ``YYYY/MM/DD-HH:MM.csv`` as UTC.

    Args:
        relative_path: Path relative to the retailer folder.

    Returns:
        UTC datetime, or ``None`` if the path does not match the layout.
    """
    match = _SNAPSHOT_NAME.match(relative_path)
    if match is None:
        return None
    parts = {key: int(value) for key, value in match.groupdict().items()}
    return datetime(
        parts["year"],
        parts["month"],
        parts["day"],
        parts["hour"],
        parts["minute"],
        tzinfo=UTC,
    )


def sha256_file(path: Path) -> str:
    """Return the hex SHA-256 digest of a file.

    Args:
        path: File to hash.

    Returns:
        Lowercase hex digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_retailer_dirs(data_dir: Path) -> Iterator[tuple[str, Path]]:
    """Yield ``(retailer, path)`` for known retailer folders under ``data_dir``.

    Args:
        data_dir: Root ``data/`` directory.

    Yields:
        Retailer slug and absolute folder path when the folder exists.
    """
    for retailer in RETAILERS:
        folder = data_dir / f"{retailer}-ch-products"
        if folder.is_dir():
            yield retailer, folder


def parse_csv_snapshot(
    *,
    retailer: str,
    path: Path,
    data_dir: Path,
    retailer_dir: Path,
) -> ParsedCsvSnapshot:
    """Parse one CSV into observations and deferred rows.

    Args:
        retailer: Retailer slug.
        path: Absolute path to the CSV.
        data_dir: Root ``data/`` directory (for relative ``source_path``).
        retailer_dir: Retailer folder used for timestamp parsing.

    Returns:
        Parsed snapshot payload for ``import_snapshot``.

    Raises:
        ValueError: If the snapshot timestamp cannot be parsed from the path.
    """
    source_namespace = namespace_for_retailer(retailer)
    try:
        relative_path = path.resolve().relative_to(data_dir.resolve()).as_posix()
    except ValueError:
        relative_path = path.name

    snapshot_rel = relative_under_retailer_dir(path, retailer_dir)
    observed_at = parse_snapshot_timestamp(snapshot_rel)
    if observed_at is None:
        msg = f"Cannot parse snapshot timestamp from {path}"
        raise ValueError(msg)

    checksum = sha256_file(path)
    observations: list[ProductObservation] = []
    deferred: list[tuple[str, str]] = []

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            url = (row.get("url") or "").strip()
            name = (row.get("name") or "").strip()
            if not name or not url:
                deferred.append((url or name or "<empty>", "missing name or url"))
                continue
            try:
                identity = extract_source_identity(retailer=retailer, url=url)
            except UntrustedSourceIdentityError as exc:
                deferred.append((url, str(exc)))
                continue
            try:
                shelf_price = _required_decimal(row.get("price"), field="price")
            except (InvalidOperation, ValueError) as exc:
                deferred.append((url, f"invalid price: {exc}"))
                continue
            observations.append(
                ProductObservation(
                    identity=identity,
                    name=name,
                    name_de=_blank_to_none(row.get("name_de")),
                    product_url=url,
                    image_url=_blank_to_none(row.get("image_url")),
                    shelf_price=shelf_price,
                    currency="CHF",
                    price_text=_blank_to_none(row.get("price_text")),
                    unit=_blank_to_none(row.get("unit")),
                    unit_price=_optional_decimal(row.get("unit_price")),
                    original_price=_optional_decimal(row.get("original_price")),
                    original_unit=_blank_to_none(row.get("original_unit")),
                    original_unit_price=_optional_decimal(
                        row.get("original_unit_price")
                    ),
                    has_discount=_optional_bool(row.get("has_discount")),
                    discount_info=_blank_to_none(row.get("discount_info")),
                    source_category=_blank_to_none(row.get("category")),
                    unified_category=_blank_to_none(row.get("unified_category")),
                    unified_subcategory=_blank_to_none(row.get("unified_subcategory")),
                )
            )

    return ParsedCsvSnapshot(
        retailer=retailer,
        source_namespace=source_namespace,
        path=path,
        relative_path=relative_path,
        source_observed_at=observed_at,
        content_checksum=checksum,
        observations=tuple(observations),
        deferred=tuple(deferred),
    )


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _required_decimal(value: str | None, *, field: str) -> Decimal:
    text = (value or "").strip()
    if not text:
        msg = f"missing {field}"
        raise ValueError(msg)
    return Decimal(text)


def _optional_decimal(value: str | None) -> Decimal | None:
    text = (value or "").strip()
    if not text:
        return None
    return Decimal(text)


def _optional_bool(value: str | None) -> bool | None:
    text = (value or "").strip().lower()
    if not text:
        return None
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None
