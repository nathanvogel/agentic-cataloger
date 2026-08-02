"""API role: minimal FastAPI health endpoints on port 3020."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from psycopg import AsyncConnection

API_HOST = "0.0.0.0"
API_PORT = 3020


def create_app() -> FastAPI:
    """Build the FastAPI app with ``/health`` and ``/ready`` endpoints.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(title="pricecomp", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Return liveness status."""
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> JSONResponse:
        """Return readiness after a lightweight database probe.

        Returns:
            ``200`` when ``DATABASE_URL`` connects; ``503`` otherwise.
        """
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "DATABASE_URL unset"},
            )
        try:
            async with await AsyncConnection.connect(
                database_url,
                connect_timeout=5,
            ) as conn:
                await conn.execute("SELECT 1")
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "database_unreachable"},
            )
        return JSONResponse(content={"status": "ready"})

    return app


def run_api() -> None:
    """Serve the API role on ``API_HOST``:``API_PORT`` via uvicorn."""
    uvicorn.run(
        "pricecomp.platform.roles.api:create_app",
        factory=True,
        host=API_HOST,
        port=API_PORT,
        log_level="info",
    )
