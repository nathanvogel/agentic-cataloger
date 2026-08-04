"""Review domain errors.

No leaf errors are known-needed yet for write/read-only 3.1 scope —
``defer_item`` has no domain-level rejection condition today, it just
persists. Basic input-shape checks use plain ``ValueError``, matching
``taxonomy/commands.py``'s convention of mixing bare ``ValueError`` with
the custom hierarchy. The base is left importable so later stages (4.4/4.5,
extract in 3.5) can add leaves without changing this file's shape.
"""

from __future__ import annotations


class ReviewError(Exception):
    """Base error for review operations."""
