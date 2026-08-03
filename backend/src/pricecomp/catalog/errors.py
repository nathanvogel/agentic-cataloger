"""Catalog domain errors."""

from __future__ import annotations


class CatalogError(Exception):
    """Base error for catalog operations."""


class UntrustedSourceIdentityError(CatalogError):
    """Raised when a source record has no trustworthy stable identity."""


class IdentityPolicyConflictError(CatalogError):
    """Raised when a namespace already uses a different identity policy version."""
