"""Telemetry Protocol contract: fake / no-op / leaf LLM span shape."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from uuid import uuid4

import pytest

from agentic_cataloger.pipeline.ports import AttributeValue, SpanHandle, Telemetry
from agentic_cataloger.platform.llm.openrouter import (
    LlmCompletion,
    record_leaf_llm_span,
    run_telemetry_smoke,
)
from agentic_cataloger.platform.telemetry.noop import NoOpTelemetry


@dataclass
class _RecordedSpan:
    name: str
    attributes: dict[str, AttributeValue]
    span_id: str
    parent_id: str | None
    ended: bool = False


@dataclass
class RecordingSpanHandle:
    """Test double for ``SpanHandle`` that mutates a recorded span."""

    _span: _RecordedSpan
    _telemetry: RecordingTelemetry

    def set_attribute(self, key: str, value: AttributeValue) -> None:
        self._span.attributes[key] = value

    def end(self) -> None:
        self._span.ended = True
        self._telemetry._pop_current(self._span.span_id)


@dataclass
class RecordingTelemetry:
    """In-memory ``Telemetry`` that captures spans for assertions."""

    spans: list[_RecordedSpan] = field(default_factory=list)
    _stack: list[str] = field(default_factory=list)
    _trace_id: str = field(default_factory=lambda: uuid4().hex)

    def start_span(
        self,
        name: str,
        *,
        attributes: Mapping[str, AttributeValue] | None = None,
    ) -> SpanHandle:
        parent_id = self._stack[-1] if self._stack else None
        recorded = _RecordedSpan(
            name=name,
            attributes=dict(attributes or {}),
            span_id=uuid4().hex,
            parent_id=parent_id,
        )
        self.spans.append(recorded)
        self._stack.append(recorded.span_id)
        return RecordingSpanHandle(_span=recorded, _telemetry=self)

    def current_trace_id(self) -> str | None:
        if not self.spans:
            return None
        return self._trace_id

    def shutdown(self) -> None:
        """No-op for the in-memory test double."""
        _ = self

    def _pop_current(self, span_id: str) -> None:
        if self._stack and self._stack[-1] == span_id:
            self._stack.pop()


def test_fake_telemetry_passes_attributes_through() -> None:
    telemetry = RecordingTelemetry()
    as_port: Telemetry = telemetry
    handle = as_port.start_span(
        "unit.test",
        attributes={"llm.provider": "openrouter"},
    )
    handle.set_attribute("llm.model_name", "test-model")
    handle.end()

    assert len(telemetry.spans) == 1
    span = telemetry.spans[0]
    assert span.ended
    assert span.attributes["llm.provider"] == "openrouter"
    assert span.attributes["llm.model_name"] == "test-model"
    assert as_port.current_trace_id() == telemetry._trace_id


def test_noop_telemetry_does_not_raise() -> None:
    telemetry: Telemetry = NoOpTelemetry()
    handle = telemetry.start_span("noop", attributes={"k": "v"})
    handle.set_attribute("extra", 1)
    handle.end()
    assert telemetry.current_trace_id() is None
    telemetry.shutdown()


def test_record_leaf_llm_span_emits_exactly_one_llm_span() -> None:
    telemetry = RecordingTelemetry()
    completion = LlmCompletion(
        text="ok",
        model_name="openai/gpt-4o-mini",
        prompt_tokens=3,
        completion_tokens=1,
        total_tokens=4,
    )

    _result, trace_id = record_leaf_llm_span(
        telemetry,
        name="telemetry.smoke",
        complete=lambda: completion,
        model_name=completion.model_name,
    )

    assert trace_id == telemetry._trace_id
    llm_spans = [
        s
        for s in telemetry.spans
        if s.attributes.get("openinference.span.kind") == "LLM"
    ]
    assert len(llm_spans) == 1
    leaf = llm_spans[0]
    assert leaf.ended
    assert leaf.attributes["llm.provider"] == "openrouter"
    assert leaf.attributes["llm.model_name"] == "openai/gpt-4o-mini"
    assert leaf.attributes["llm.token_count.prompt"] == 3
    assert leaf.attributes["llm.token_count.completion"] == 1
    assert leaf.attributes["llm.token_count.total"] == 4
    _assert_no_llm_parent_of_llm(telemetry.spans)


def test_record_leaf_llm_span_runs_complete_while_span_open() -> None:
    telemetry = RecordingTelemetry()
    seen_open: list[bool] = []

    def complete() -> LlmCompletion:
        seen_open.append(bool(telemetry._stack))
        return LlmCompletion(text="ok", model_name="m")

    record_leaf_llm_span(
        telemetry,
        name="telemetry.smoke",
        complete=complete,
        model_name="m",
    )

    assert seen_open == [True]
    assert telemetry.spans[0].ended


def test_smoke_helper_with_injected_completion_is_leaf_llm() -> None:
    telemetry = RecordingTelemetry()
    completion = LlmCompletion(text="ok", model_name="injected-model")

    run_telemetry_smoke(
        telemetry,
        api_key="test-key",
        model="injected-model",
        complete=lambda: completion,
    )

    llm_spans = [
        s
        for s in telemetry.spans
        if s.attributes.get("openinference.span.kind") == "LLM"
    ]
    assert len(llm_spans) == 1
    assert llm_spans[0].attributes["llm.provider"] == "openrouter"
    _assert_no_llm_parent_of_llm(telemetry.spans)


def test_smoke_requires_openrouter_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    telemetry = RecordingTelemetry()
    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        run_telemetry_smoke(telemetry)


def _assert_no_llm_parent_of_llm(spans: list[_RecordedSpan]) -> None:
    by_id = {s.span_id: s for s in spans}
    for span in spans:
        if span.attributes.get("openinference.span.kind") != "LLM":
            continue
        if span.parent_id is None:
            continue
        parent = by_id[span.parent_id]
        assert parent.attributes.get("openinference.span.kind") != "LLM"
