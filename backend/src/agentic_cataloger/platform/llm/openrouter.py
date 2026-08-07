"""OpenRouter chat helper and telemetry smoke (leaf LLM span)."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from phoenix.otel import OpenInferenceSpanKindValues, SpanAttributes

from agentic_cataloger.pipeline.ports import AttributeValue, SpanHandle, Telemetry

if TYPE_CHECKING:
    from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL: Final = "https://openrouter.ai/api/v1"
DEFAULT_SMOKE_MODEL: Final = "openai/gpt-4o-mini"
# Same default model as the smoke path — cheap and already proven to work
# against OpenRouter; override with PIPELINE_MODEL for a stronger model.
DEFAULT_PIPELINE_MODEL: Final = "openai/gpt-4o-mini"
PIPELINE_LLM_TIMEOUT_SECONDS: Final = 60.0

# OpenInference keys via phoenix.otel re-exports (platform only; domain stays SDK-free)
SPAN_KIND_KEY: Final = SpanAttributes.OPENINFERENCE_SPAN_KIND
SPAN_KIND_LLM: Final = OpenInferenceSpanKindValues.LLM.value
LLM_PROVIDER_KEY: Final = SpanAttributes.LLM_PROVIDER
LLM_PROVIDER_OPENROUTER: Final = "openrouter"
LLM_MODEL_NAME_KEY: Final = SpanAttributes.LLM_MODEL_NAME
LLM_ATTR_PROMPT_COUNT: Final = SpanAttributes.LLM_TOKEN_COUNT_PROMPT
LLM_ATTR_COMPLETION_COUNT: Final = SpanAttributes.LLM_TOKEN_COUNT_COMPLETION
LLM_ATTR_TOTAL_COUNT: Final = SpanAttributes.LLM_TOKEN_COUNT_TOTAL

_SMOKE_PROMPT: Final = "Reply with exactly one word: ok"


@dataclass(frozen=True, slots=True)
class LlmCompletion:
    """One chat completion result with optional token usage."""

    text: str
    model_name: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


def _set_usage_attributes(handle: SpanHandle, completion: LlmCompletion) -> None:
    """Attach model + token attrs once the completion is known."""
    handle.set_attribute(LLM_MODEL_NAME_KEY, completion.model_name)
    if completion.prompt_tokens is not None:
        handle.set_attribute(LLM_ATTR_PROMPT_COUNT, completion.prompt_tokens)
    if completion.completion_tokens is not None:
        handle.set_attribute(LLM_ATTR_COMPLETION_COUNT, completion.completion_tokens)
    if completion.total_tokens is not None:
        handle.set_attribute(LLM_ATTR_TOTAL_COUNT, completion.total_tokens)


def record_leaf_llm_span(
    telemetry: Telemetry,
    *,
    name: str,
    complete: Callable[[], LlmCompletion],
    model_name: str,
    provider: str = LLM_PROVIDER_OPENROUTER,
) -> tuple[LlmCompletion, str | None]:
    """Run ``complete`` inside one leaf LLM span and return result + trace id.

    The span starts before ``complete`` and ends after, so latency covers the
    actual LLM (or injected) call rather than attribute bookkeeping.

    Args:
        telemetry: Application telemetry port.
        name: Span name (e.g. ``telemetry.smoke``).
        complete: Callable that performs the chat completion.
        model_name: Model id set on the span before the call (may be refined
            from the completion afterward).
        provider: Value for ``llm.provider`` (default ``openrouter``).

    Returns:
        The completion and current trace id hex (``None`` under no-op).
    """
    attributes: dict[str, AttributeValue] = {
        SPAN_KIND_KEY: SPAN_KIND_LLM,
        LLM_PROVIDER_KEY: provider,
        LLM_MODEL_NAME_KEY: model_name,
    }
    handle = telemetry.start_span(name, attributes=attributes)
    try:
        completion = complete()
        _set_usage_attributes(handle, completion)
        return completion, telemetry.current_trace_id()
    finally:
        handle.end()


def complete_openrouter(
    *,
    api_key: str,
    model: str,
    prompt: str = _SMOKE_PROMPT,
) -> LlmCompletion:
    """Run one cheap OpenRouter chat completion via ``langchain-openai``.

    Args:
        api_key: OpenRouter API key (never logged).
        model: OpenRouter model id.
        prompt: User message (tiny by default for smoke).

    Returns:
        Completion text and usage when the response includes it.
    """
    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    llm = ChatOpenAI(
        model=model,
        api_key=SecretStr(api_key),
        base_url=OPENROUTER_BASE_URL,
        max_completion_tokens=16,
        temperature=0,
    )
    message = llm.invoke(prompt)
    text = message.content if isinstance(message.content, str) else str(message.content)
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    usage = getattr(message, "usage_metadata", None)
    if isinstance(usage, dict):
        prompt_tokens = usage.get("input_tokens")
        completion_tokens = usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")
    return LlmCompletion(
        text=text,
        model_name=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )


def chat_model() -> ChatOpenAI:
    """Build the shared chat model for pipeline stages (OpenRouter-backed).

    Model comes from ``PIPELINE_MODEL`` (default ``openai/gpt-4o-mini``,
    same as the smoke path). ``max_retries=0`` is deliberate: LangGraph's
    node-level ``RetryPolicy`` owns retries, not the client — a client-side
    retry inside a ``RetryPolicy``-wrapped node would silently multiply
    spend and hide the failure from the attempt counter.

    Returns:
        Configured chat model — no tools or structured output bound yet;
        ``langchain.agents.create_agent`` does that per stage.

    Raises:
        ValueError: ``OPENROUTER_API_KEY`` is unset.
    """
    from langchain_openai import ChatOpenAI
    from pydantic import SecretStr

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        msg = "OPENROUTER_API_KEY is required for pipeline stages"
        raise ValueError(msg)
    model = os.environ.get("PIPELINE_MODEL") or DEFAULT_PIPELINE_MODEL
    return ChatOpenAI(
        model=model,
        api_key=SecretStr(api_key),
        base_url=OPENROUTER_BASE_URL,
        temperature=0,
        timeout=PIPELINE_LLM_TIMEOUT_SECONDS,
        max_retries=0,
    )


def run_telemetry_smoke(
    telemetry: Telemetry,
    *,
    api_key: str | None = None,
    model: str | None = None,
    complete: Callable[[], LlmCompletion] | None = None,
) -> str | None:
    """One OpenRouter completion + one leaf LLM span (no live call if ``complete``).

    Args:
        telemetry: Configured telemetry port.
        api_key: OpenRouter key; defaults to ``OPENROUTER_API_KEY``.
        model: Model id; defaults to ``OPENROUTER_SMOKE_MODEL`` or gpt-4o-mini.
        complete: Optional injectable completion (unit tests; skips network).

    Returns:
        Trace id from the leaf span, or ``None`` under no-op telemetry.

    Raises:
        ValueError: When no API key is available and ``complete`` was not passed.
    """
    key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
    if complete is None and not key:
        raise ValueError(
            "OPENROUTER_API_KEY is required for telemetry smoke "
            "(or pass complete= for offline tests)",
        )
    model_id = model or os.environ.get("OPENROUTER_SMOKE_MODEL") or DEFAULT_SMOKE_MODEL
    if complete is not None:
        completer = complete
    else:
        if key is None:
            raise ValueError(
                "OPENROUTER_API_KEY is required for telemetry smoke "
                "(or pass complete= for offline tests)",
            )
        logger.info("OpenRouter smoke model=%s", model_id)

        def completer() -> LlmCompletion:
            return complete_openrouter(api_key=key, model=model_id)

    _completion, trace_id = record_leaf_llm_span(
        telemetry,
        name="telemetry.smoke",
        complete=completer,
        model_name=model_id,
    )
    return trace_id
