"""Persistence adapter package.

App-role DB access goes through ``db.connect_app`` / ``db.get_app_pool``.
A borrowed ``Connection`` is exclusive to one sequential caller — see
``db`` module docs.
"""

from agentic_cataloger.platform.persistence.db import (
    close_app_pools,
    connect_app,
    get_app_pool,
)

__all__ = [
    "close_app_pools",
    "connect_app",
    "get_app_pool",
]
