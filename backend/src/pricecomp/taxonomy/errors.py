"""Taxonomy domain errors."""

from __future__ import annotations


class TaxonomyError(Exception):
    """Base error for taxonomy operations."""


class CategoryNotFoundError(TaxonomyError):
    """Raised when a category id is missing."""


class ProductNotFoundError(TaxonomyError):
    """Raised when a catalog product id is missing."""


class CycleError(TaxonomyError):
    """Raised when a reparent would introduce a cycle."""


class SelfParentError(TaxonomyError):
    """Raised when a category would become its own parent."""


class NotLeafError(TaxonomyError):
    """Raised when assign targets a non-leaf category."""


class NonLeafHasMembersError(TaxonomyError):
    """Raised when a membered category would stop being a leaf."""


class RootAlreadyExistsError(TaxonomyError):
    """Raised when creating a second root category."""
