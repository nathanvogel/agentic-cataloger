"""Unit tests for durable source identity extraction and UTC helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from pricecomp.catalog.errors import UntrustedSourceIdentityError
from pricecomp.catalog.identity import (
    IDENTITY_POLICY_VERSION,
    extract_source_identity,
    namespace_for_retailer,
)
from pricecomp.catalog.timeutil import ensure_utc


def test_extract_migros_product_id() -> None:
    """Migros identity comes from /product/{id}."""
    identity = extract_source_identity(
        retailer="migros",
        url="https://www.migros.ch/de/product/263406106500",
    )
    assert identity.source_namespace == "migros-ch"
    assert identity.source_product_id == "263406106500"
    assert identity.source_variant_id is None


def test_extract_lidl_view_id() -> None:
    """Lidl identity uses Magento view/id, not the slug SKU."""
    identity = extract_source_identity(
        retailer="lidl",
        url=(
            "https://sortiment.lidl.ch/de/catalog/product/view/id/20804/"
            "s/vegane-gerichte-asiatisch-5107760/category/171/"
        ),
    )
    assert identity.source_namespace == "lidl-ch"
    assert identity.source_product_id == "20804"
    assert identity.source_variant_id is None


def test_extract_coop_product_id() -> None:
    """Coop identity comes from trailing /p/{id}."""
    identity = extract_source_identity(
        retailer="coop",
        url=(
            "https://www.coop.ch/de/lebensmittel/fruechte-gemuese/fruechte/"
            "bananen/naturaplan-bio-fairtrade-bananen-ca/p/6495669"
        ),
    )
    assert identity.source_namespace == "coop-ch"
    assert identity.source_product_id == "6495669"


def test_extract_denner_product_and_variant() -> None:
    """Denner carries product id and optional variant query param."""
    identity = extract_source_identity(
        retailer="denner",
        url=(
            "https://www.denner.ch/de/aktionen-und-sortiment/"
            "litschis-offenverkauf~p1101270"
            "?variant=2c8381d3-be7d-41c5-b852-b2a5aff21021"
        ),
    )
    assert identity.source_namespace == "denner-ch"
    assert identity.source_product_id == "1101270"
    assert identity.source_variant_id == "2c8381d3-be7d-41c5-b852-b2a5aff21021"


def test_untrusted_url_defers() -> None:
    """Missing trustworthy ID raises — never synthesize from name/URL host."""
    with pytest.raises(UntrustedSourceIdentityError):
        extract_source_identity(
            retailer="migros",
            url="https://www.migros.ch/de/search?q=milk",
        )


def test_empty_url_defers() -> None:
    """Empty URL is untrusted."""
    with pytest.raises(UntrustedSourceIdentityError):
        extract_source_identity(retailer="migros", url="  ")


def test_identity_policy_version_is_declared() -> None:
    """Adapter declares a versioned normalization policy."""
    assert IDENTITY_POLICY_VERSION.startswith("yelinz-csv-identity@")
    assert namespace_for_retailer("migros") == "migros-ch"


def test_ensure_utc_interprets_naive_as_utc() -> None:
    """Naive source-observed times are treated as UTC."""
    naive = datetime(2025, 12, 30, 15, 22)
    assert ensure_utc(naive) == datetime(2025, 12, 30, 15, 22, tzinfo=UTC)


def test_ensure_utc_converts_non_utc() -> None:
    """Aware non-UTC inputs convert to UTC."""
    plus_two = timezone(timedelta(hours=2))
    local = datetime(2025, 12, 30, 17, 22, tzinfo=plus_two)
    assert ensure_utc(local) == datetime(2025, 12, 30, 15, 22, tzinfo=UTC)
