"""Platform telemetry adapters (Phoenix / no-op)."""

from agentic_cataloger.platform.telemetry.bootstrap import (
    configure_telemetry,
    reset_telemetry_for_tests,
    shutdown_telemetry,
)
from agentic_cataloger.platform.telemetry.noop import NoOpTelemetry
from agentic_cataloger.platform.telemetry.phoenix_adapter import PhoenixTelemetry

__all__ = [
    "NoOpTelemetry",
    "PhoenixTelemetry",
    "configure_telemetry",
    "reset_telemetry_for_tests",
    "shutdown_telemetry",
]
