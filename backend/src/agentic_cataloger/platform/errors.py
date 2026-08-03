"""Application errors for platform process roles."""

from __future__ import annotations


class MigrateError(Exception):
    """Base error for migrate-role failures."""


class DatabaseNotReadyError(MigrateError):
    """A required database or HTTP endpoint did not become ready."""


class BootstrapError(MigrateError):
    """A bootstrap step failed (catalog check, alembic, or verification)."""
