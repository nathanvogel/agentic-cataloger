"""Catalog domain errors."""

from __future__ import annotations


class CatalogError(Exception):
    """Base error for catalog operations."""


class UntrustedSourceIdentityError(CatalogError):
    """Raised when a source record has no trustworthy stable identity."""


class SourceIdentityCollisionError(CatalogError):
    """Raised when two records in one snapshot share the same source identity."""


class IdentityPolicyConflictError(CatalogError):
    """Raised when a namespace already uses a different identity policy version."""
