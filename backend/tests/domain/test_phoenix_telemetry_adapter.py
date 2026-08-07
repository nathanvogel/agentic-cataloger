"""Phoenix telemetry adapter + bootstrap (offline; no live Phoenix/OpenRouter)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from agentic_cataloger.platform.llm.openrouter import (
    LlmCompletion,
    record_leaf_llm_span,
)
from agentic_cataloger.platform.telemetry.bootstrap import (
    configure_telemetry,
    reset_telemetry_for_tests,
    shutdown_telemetry,
)
from agentic_cataloger.platform.telemetry.noop import NoOpTelemetry
from agentic_cataloger.platform.telemetry.phoenix_adapter import PhoenixTelemetry


def test_configure_telemetry_noop_when_endpoint_unset(
    monkeypatch: Any,
) -> None:
    reset_telemetry_for_tests()
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    with patch("phoenix.otel.register") as register:
        telemetry = configure_telemetry()
        register.assert_not_called()
    assert isinstance(telemetry, NoOpTelemetry)
    handle = telemetry.start_span("x")
    handle.end()
    assert telemetry.current_trace_id() is None
    shutdown_telemetry()
    reset_telemetry_for_tests()


def test_configure_telemetry_calls_register_with_traces_endpoint(
    monkeypatch: Any,
) -> None:
    reset_telemetry_for_tests()
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://phoenix:6006")
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "test-project")

    fake_provider = MagicMock()
    fake_tracer = MagicMock()
    fake_provider.get_tracer.return_value = fake_tracer

    with patch(
        "phoenix.otel.register",
        return_value=fake_provider,
    ) as register:
        telemetry = configure_telemetry()
        register.assert_called_once_with(
            project_name="test-project",
            endpoint="http://phoenix:6006/v1/traces",
            protocol="http/protobuf",
            batch=False,
            auto_instrument=True,
        )
    assert isinstance(telemetry, PhoenixTelemetry)
    shutdown_telemetry()
    reset_telemetry_for_tests()


def test_otlp_http_traces_endpoint_appends_path_once() -> None:
    from agentic_cataloger.platform.telemetry.bootstrap import (
        otlp_http_traces_endpoint,
    )

    assert (
        otlp_http_traces_endpoint("http://phoenix:6006")
        == "http://phoenix:6006/v1/traces"
    )
    assert (
        otlp_http_traces_endpoint("http://phoenix:6006/v1/traces")
        == "http://phoenix:6006/v1/traces"
    )
    assert (
        otlp_http_traces_endpoint("http://localhost:3022/")
        == "http://localhost:3022/v1/traces"
    )


def test_phoenix_adapter_records_leaf_llm_attrs() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")
    telemetry = PhoenixTelemetry(tracer, provider=None)

    completion = LlmCompletion(
        text="ok",
        model_name="openai/gpt-4o-mini",
        prompt_tokens=2,
        completion_tokens=1,
        total_tokens=3,
    )
    _result, trace_id = record_leaf_llm_span(
        telemetry,
        name="telemetry.smoke",
        complete=lambda: completion,
        model_name=completion.model_name,
    )

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "telemetry.smoke"
    assert span.attributes is not None
    assert span.attributes["openinference.span.kind"] == "LLM"
    assert span.attributes["llm.provider"] == "openrouter"
    assert span.attributes["llm.model_name"] == "openai/gpt-4o-mini"
    assert span.attributes["llm.token_count.prompt"] == 2
    assert span.attributes["llm.token_count.completion"] == 1
    assert span.attributes["llm.token_count.total"] == 3
    assert trace_id is not None
    assert len(trace_id) == 32
    # Duration must cover the (injected) call window, not be a zero-width stamp.
    assert span.end_time is not None and span.start_time is not None
    assert span.end_time >= span.start_time
    provider.shutdown()


def test_phoenix_adapter_current_trace_id_none_when_idle() -> None:
    provider = TracerProvider()
    # Ensure no leftover current span from other tests
    trace.use_span(trace.INVALID_SPAN, end_on_exit=False)
    telemetry = PhoenixTelemetry(provider.get_tracer("idle"))
    assert telemetry.current_trace_id() is None
    provider.shutdown()
