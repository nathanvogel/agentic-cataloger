"""Durable source identity and retailer URL extractors.

Identity is ``(source_namespace, source_product_id, source_variant_id?)``.
Name and URL are observations — never used to synthesize an ID.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from pricecomp.catalog.errors import UntrustedSourceIdentityError

# Versioned normalization policy recorded on every import (1.5-UNIT-002 / 1.5-INT-007).
IDENTITY_POLICY_VERSION = "yelinz-csv-identity@1"

_MIGROS_PRODUCT = re.compile(r"/product/(\d+)/?$", re.IGNORECASE)
_LIDL_VIEW_ID = re.compile(r"/view/id/(\d+)(?:/|$)", re.IGNORECASE)
_COOP_PRODUCT = re.compile(r"/p/(\d+)/?$", re.IGNORECASE)
_DENNER_PRODUCT = re.compile(r"~p(\d+)", re.IGNORECASE)

_NAMESPACE_BY_RETAILER = {
    "migros": "migros-ch",
    "lidl": "lidl-ch",
    "coop": "coop-ch",
    "denner": "denner-ch",
}


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    """Stable external product key from a versioned adapter."""

    source_namespace: str
    source_product_id: str
    source_variant_id: str | None = None


def namespace_for_retailer(retailer: str) -> str:
    """Map a retailer folder slug to its source namespace.

    Args:
        retailer: One of ``migros``, ``lidl``, ``coop``, ``denner``.

    Returns:
        Source namespace string (e.g. ``migros-ch``).

    Raises:
        ValueError: If the retailer is unknown.
    """
    key = retailer.strip().lower()
    try:
        return _NAMESPACE_BY_RETAILER[key]
    except KeyError as exc:
        msg = (
            f"Unknown retailer {retailer!r}; "
            f"expected one of {sorted(_NAMESPACE_BY_RETAILER)}"
        )
        raise ValueError(msg) from exc


def extract_source_identity(*, retailer: str, url: str) -> SourceIdentity:
    """Extract durable source identity from a product URL.

    Args:
        retailer: Retailer slug (``migros``, ``lidl``, ``coop``, ``denner``).
        url: Product page URL from the CSV.

    Returns:
        Parsed ``SourceIdentity``.

    Raises:
        UntrustedSourceIdentityError: When the URL has no trustworthy stable ID.
    """
    namespace = namespace_for_retailer(retailer)
    cleaned = (url or "").strip()
    if not cleaned:
        raise UntrustedSourceIdentityError(
            f"Empty product URL for namespace {namespace}"
        )

    parsed = urlparse(cleaned)
    path = parsed.path or ""

    if namespace == "migros-ch":
        match = _MIGROS_PRODUCT.search(path)
        if match:
            return SourceIdentity(namespace, match.group(1))
    elif namespace == "lidl-ch":
        match = _LIDL_VIEW_ID.search(path)
        if match:
            return SourceIdentity(namespace, match.group(1))
    elif namespace == "coop-ch":
        match = _COOP_PRODUCT.search(path)
        if match:
            return SourceIdentity(namespace, match.group(1))
    elif namespace == "denner-ch":
        match = _DENNER_PRODUCT.search(path)
        if match:
            variant = _denner_variant(parsed.query)
            return SourceIdentity(namespace, match.group(1), variant)

    raise UntrustedSourceIdentityError(
        f"No trustworthy source ID in URL for {namespace}: {cleaned!r}"
    )


def _denner_variant(query: str) -> str | None:
    values = parse_qs(query).get("variant", [])
    if not values:
        return None
    variant = values[0].strip()
    return variant or None
