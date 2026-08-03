"""UTC helpers for catalog ingest."""

from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc(value: datetime) -> datetime:
    """Interpret a source-observed datetime as UTC.

    Naive datetimes are treated as UTC. Aware datetimes are converted to UTC.

    Args:
        value: Source-observed timestamp (naive or aware).

    Returns:
        Timezone-aware UTC datetime.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
