"""Unit tests for the process-wide app connection pool."""

from __future__ import annotations

from agentic_cataloger.platform.persistence.db import (
    close_app_pools,
    get_app_pool,
)


def test_get_app_pool_reuses_same_instance_per_url() -> None:
    """Same URL returns the same open pool; close clears the registry."""
    close_app_pools()
    url = "postgresql://agentic_cataloger_app:x@127.0.0.1:1/unused"
    try:
        first = get_app_pool(url, min_size=0, max_size=1)
        second = get_app_pool(url, min_size=0, max_size=1)
        assert first is second
        assert not first.closed
    finally:
        close_app_pools()
    # After close, a new call allocates a fresh pool object.
    third = get_app_pool(url, min_size=0, max_size=1)
    try:
        assert third is not first
        assert not third.closed
    finally:
        close_app_pools()
