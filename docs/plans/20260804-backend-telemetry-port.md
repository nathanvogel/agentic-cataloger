# Dev Plan: Telemetry port + phoenix.otel + OpenRouter smoke (roadmap 4.3)

- **Date**: 2026-08-04
- **Author**: planning agent (plan-task)
- **Status**: Draft
- **Primary services**: `backend`
- **Related specs / ADRs**: [architecture.md § Observability](../specs/architecture.md), [roadmap.md M2 **4.3**](roadmap.md), [code_style_python.md §5 Protocols](../specs/code_style_python.md). Cross-ref: **4.1** / **3.1** design (run_id-only vocabulary, `DeferredItem.trace_id`) — decided on branch discussion for contracts + deferred_items; this plan does not implement those items.

## 1. Problem

Debugging LLM stages without traces is the slowest way to build the agent. Roadmap **4.3** asks for a domain/application-owned telemetry port with OpenTelemetry only in adapters, exporting to the self-hosted Phoenix already in Compose. We need that scaffolding *before* discover/assign stages (**4.4**), and a cheap real OpenRouter call so Phoenix shows a leaf LLM span with the attrs **4.6** will later use for cost checks.

## 2. Goals and non-goals

**Goals**

- Ship a thin `Telemetry` Protocol (start/end span, attributes, current trace id) with zero `opentelemetry` / `phoenix` / LangChain imports in domain packages.
- Implement a platform adapter via lightweight **`arize-phoenix-otel`** (`phoenix.otel.register`) when `PHOENIX_COLLECTOR_ENDPOINT` is set, plus `NoOpTelemetry` when it is unset.
- Add `agentic-cataloger telemetry smoke` that calls a cheap OpenRouter model via existing `langchain-openai` (`base_url`) and records one **leaf** LLM span (`openinference.span.kind=LLM`, `llm.provider=openrouter`, model, token counts when available).
- Document `PHOENIX_*` / OpenRouter env vars; keep CI offline (no live OpenRouter in default pytest).

**Non-goals**

- **4.1** typed run/stage contracts (`StageKind` / `StageResult` / `run_id`) — do not implement here; when attrs are set later, use that vocabulary (no minted `llm_call_id`).
- **3.1** `deferred_items`, **2.5** category search, **4.4–4.5** agent/LangGraph.
- **4.6** formal end-to-end run join + cost double-count proof (foundation only here).
- OpenInference LangChain **auto**-instrumentation (`auto_instrument=False` now; wire in **4.4**).
- Full production LLM port / multi-provider factory (this task ships the OpenRouter client path used by smoke; stages reuse it later).
- Rewriting [architecture.md](../specs/architecture.md) “OpenAI + Anthropic only” into an ADR in this PR (note the drift; file ADR when OR becomes the default stage path).
- Hand-rolling Resource / `OTLPSpanExporter` / processor wiring (use `register()` instead).
- Requiring Phoenix model-pricing setup as a hard gate (document silent `$0`).

## 3. Success criteria

- Given Phoenix is up and `OPENROUTER_API_KEY` + `PHOENIX_COLLECTOR_ENDPOINT` are set, when `agentic-cataloger telemetry smoke` runs, then Phoenix shows a trace with a leaf span kind `LLM` carrying `llm.provider` and `llm.model_name` (token count attrs when the response includes usage).
- Given `PHOENIX_COLLECTOR_ENDPOINT` is unset, when any code path uses the telemetry port, then the process does not crash; spans are discarded; **`register()` is never called** (avoids its localhost:6006 default).
- Given domain packages under `pipeline/` (and existing catalog/taxonomy), when boundary AST tests run, then no module imports `opentelemetry`, `phoenix`, or `langchain` from the port module itself.
- Artifact: code + README env docs + architecture stack-table pin for `arize-phoenix-otel`.
- Validation: domain unit tests (fake port / no-op / leaf-span shape); manual Phoenix UI check documented in README; live OpenRouter **not** in default CI.

## 4. Scope lock-in

```
SCOPE LOCK-IN
- Goal: Ship roadmap 4.3 — domain/application-owned telemetry port; Phoenix export only in adapters; prove a real cheap OpenRouter LLM leaf span shows up (attrs ready for later 4.6 cost checks).
- In scope:
  - Thin telemetry Protocol under application layer (`pipeline/`)
  - Platform adapter via `arize-phoenix-otel` (`phoenix.otel.register`) + bootstrap (`PHOENIX_COLLECTOR_ENDPOINT`; no-op when off)
  - One CLI path: cheap OpenRouter chat completion + leaf LLM span
  - Tests: port contract + adapter unit tests; live call gated / manual
  - Docs: backend README env vars for PHOENIX_*/OpenRouter
- Out of scope: 4.1 contracts, 3.1, 2.5, 4.4–4.5, 4.6 proof, OpenInference auto-instrumentation, model-pricing as hard gate, hand-rolled OTLP bootstrap
- Primary packages/services: backend (`pipeline`, `platform/` telemetry + CLI), Compose Phoenix (already present)
- Success criteria: no opentelemetry/phoenix in domain; visible leaf LLM span in Phoenix with llm.provider=openrouter; no-op when collector unset
Confirm? yes (2026-08-04)
```

**Dependency check (ordered roadmap priors still open):**

| Prior undone | Blocks 4.3? |
| --- | --- |
| **2.5** search tools | No |
| **4.1** run/stage vocabulary | Soft — vocabulary decided (`run_id` + `StageKind` + attempt `int`); 4.3 does not import `contracts`, but later stage spans use those names (not invented IDs) |
| **3.1** `deferred_items` | No (will *consume* `current_trace_id` later as nullable `trace_id`) |

## 5. Approach

1. Add `pipeline/ports.py` with `Telemetry` + `SpanHandle` Protocols (string attribute keys; no tracing SDK types).
2. Add `platform/telemetry/`: bootstrap (`configure_telemetry` / shutdown+flush), `PhoenixTelemetry` `@final` adapter (wraps the tracer from `register()`), `NoOpTelemetry`.
3. Pin **`arize-phoenix-otel>=0.16.0`** (lightweight; not full `arize-phoenix`). When `PHOENIX_COLLECTOR_ENDPOINT` is set, call `phoenix.otel.register(project_name=..., endpoint=..., batch=False, auto_instrument=False)`. That installs Phoenix-aware Resource (`openinference.project.name`), OTLP export to the UI collector port (helper appends `/v1/traces`), and **SimpleSpanProcessor** by default (CLI flush). Keep `auto_instrument=False` until **4.4**. Existing `opentelemetry-api` / `opentelemetry-sdk` pins stay; do not add a separate hand-rolled exporter package.
4. Add `platform/llm/openrouter.py` (smoke entry + thin client helper stages can reuse): `ChatOpenAI(base_url=https://openrouter.ai/api/v1, …)` one-token/tiny prompt; record a leaf LLM span via the **Telemetry** port. Prefer `llm.provider=openrouter`. In platform only, attr keys / span-kind enums may use `phoenix.otel` OpenInference re-exports (≥0.16).
5. Wire CLI: `agentic-cataloger telemetry smoke` — bootstrap → call → print trace id → force flush/shutdown.
6. Extend `pipeline` boundary AST test (mirror catalog/taxonomy). Document env in `backend/README.md`.

### 5.1 File inventory

**Create**

- `backend/src/agentic_cataloger/pipeline/ports.py` — `Telemetry` / `SpanHandle` Protocols
- `backend/src/agentic_cataloger/platform/telemetry/__init__.py`
- `backend/src/agentic_cataloger/platform/telemetry/bootstrap.py` — read `PHOENIX_*`, call `register()` or return no-op
- `backend/src/agentic_cataloger/platform/telemetry/phoenix_adapter.py` — `@final` `PhoenixTelemetry` implementing the port
- `backend/src/agentic_cataloger/platform/telemetry/noop.py` — `@final` no-op
- `backend/src/agentic_cataloger/platform/llm/openrouter.py` — OpenRouter client helper + smoke call + span recording
- `backend/src/agentic_cataloger/platform/llm/__init__.py` (optional package marker)
- `backend/tests/domain/test_pipeline_boundaries.py` — forbid adapter imports in `pipeline/`
- `backend/tests/domain/test_telemetry_port.py` — fake/`NoOp` behavior, attribute pass-through contract
- `backend/tests/domain/test_phoenix_telemetry_adapter.py` — adapter + smoke leaf-span shape without hitting a real Phoenix (fake `Telemetry`, or a test tracer provider / span capture behind the adapter)

**Modify**

- `backend/pyproject.toml` + `uv.lock` — add `arize-phoenix-otel` pin (≥0.16.0)
- `backend/src/agentic_cataloger/platform/cli.py` — `telemetry` command + help text
- `backend/README.md` — env table + smoke how-to + silent `$0` note
- `docs/specs/architecture.md` — add `arize-phoenix-otel` to stack table (keep API/SDK rows)
- `backend/tests/domain/test_structural_seed.py` — only if new packages need import smoke (likely N/A; `pipeline` already seeded)

**Delete:** N/A

**Migrations:** none

### 5.2 Data / contract changes

- **API:** none (CLI only).
- **DB:** none.
- **Env vars (document; no secrets in repo):**

| Variable | Role | Example |
| --- | --- | --- |
| `PHOENIX_COLLECTOR_ENDPOINT` | Phoenix base URL (`register()` adds `/v1/traces`); **unset → NoOpTelemetry** (do not use register’s localhost default) | `http://localhost:3022` (host) / `http://phoenix:6006` (compose) |
| `PHOENIX_PROJECT` or `PHOENIX_PROJECT_NAME` | Phoenix project (`openinference.project.name`) | `agentic-cataloger` |
| `PHOENIX_API_KEY` | Optional Bearer for authenticated Phoenix; unused for local Compose | (omit locally) |
| `OPENROUTER_API_KEY` | Smoke / future LLM hop | (local secret) |
| `OPENROUTER_SMOKE_MODEL` | Smoke model id | default a cheap OpenRouter id (pick one stable cheap model in impl; override via env) |

Do not add keys to Compose by default (keeps CI/devcontainers offline-safe). README shows export lines for local smoke. Prefer Phoenix’s `PHOENIX_*` names so they match upstream docs and `register()`.

### 5.3 External touch points

- Phoenix container already on `:3022` → `:6006` ([docker-compose.yml](../../docker-compose.yml)).
- OpenRouter HTTPS (smoke now; likely default LLM hop for a while — explicit env, not Compose secrets).
- No coordination with other packages; frontend untouched.

## 6. Pitfalls and mitigations

| Pitfall | Impact | Mitigation | Owner |
| --- | --- | --- | --- |
| Wrong collector URL (`4318`, or host:port mix-up) | Spans never appear; looks like “telemetry broken” | Document `PHOENIX_COLLECTOR_ENDPOINT` as UI base (`:3022` host / `:6006` compose); `register()` appends `/v1/traces`; unit-test enabled vs no-op gating | executor |
| Accidental `register()` with localhost default | CI/local without Phoenix still tries export | Only call `register()` when `PHOENIX_COLLECTOR_ENDPOINT` is explicitly set | executor |
| Parent + child both counted as LLM | Future **4.6** cost double-count | “Leaf” = span with no child LLM spans (trace tree, not taxonomy). Smoke emits **one** `openinference.span.kind=LLM` span; any parent must be `CHAIN`/`AGENT`/unset, never also `LLM`. Enforce with offline span-capture unit test; Phoenix join/cost e2e stays **4.6** | executor |
| Domain imports tracing SDKs | Hexagonal regression | `test_pipeline_boundaries.py` forbids `opentelemetry` / `phoenix` / `langchain` (+ existing catalog/taxonomy tests) | executor |
| Live OpenRouter in CI | Flaky/paid CI | No pytest live call by default; smoke is CLI + manual; optional `@pytest.mark` only if env set (prefer skip) | executor |
| `batch=True` + short CLI exit | Empty Phoenix | `register(..., batch=False)` (SimpleSpanProcessor default); always flush/shutdown on exit; `batch=True` only later for long-lived `api` if needed | executor |
| Missing `openinference.span.kind=LLM` | Span not rendered as LLM in Phoenix | Set kind + `llm.provider` / `llm.model_name` / token attrs explicitly on the leaf (platform may use `phoenix.otel` re-exports) | executor |
| Logging API keys | Secret leak | Never log `OPENROUTER_API_KEY` / `PHOENIX_API_KEY`; fail closed with clear “missing key” | executor |
| Compose topology test churn | CI noise | Do not require new compose env for collector/OpenRouter; README-only defaults | executor |
| Blast: `deferred_items.trace_id` (**3.1**) | Needs stable trace id string (nullable) | Expose `current_trace_id()` now (no-op → `None` is fine); **3.1** `defer_item` accepts optional `trace_id`; stages wire it in **4.4** | follow-up |
| Blast: inventing stage/LLM-call IDs as span attrs | Conflicts with **4.1** (run_id only) | Do **not** mint `stage_execution_id` / `stage_attempt_id` / `llm_call_id` attrs. OTel span id is the call identity; stage label / attempt int only when stages exist | executor |
| Blast: **4.6** cost | Silent `$0` without pricing entry | README note; accepted for 4.3 | accepted |

Accepted risks:

- Cost may show `$0` until operator adds a Phoenix model-pricing entry matching the smoke model name (and `llm.provider`, prefer `openrouter` so pricing patterns stay one hop).
- Architecture text still says “OpenAI + Anthropic via LangChain”; product intent is to **keep OpenRouter for a while** (one bill, one API, easier model swap for tests/o11y). No ADR in this PR; stages can keep calling through the same OpenRouter client until that doc is updated.

## 7. Technical decisions

### Decision: Port lives in `pipeline/ports.py`

- **Choice**: Application port under empty `pipeline/` package.
- **Options considered**: A) `pipeline/ports.py`, B) `contracts/` next to future 4.1 IDs, C) new top-level `observability/` package.
- **Why**: Architecture already lists telemetry as application-layer; `pipeline/` is the future consumer of run/stage tracing; matches catalog/taxonomy “ports in owning package” without inventing a package.
- **Rejected because**: B — `contracts/` owns `StageKind` / `StageResult` (**4.1**), not adapter ports; putting `Telemetry` there would blur that split. C — YAGNI.

### Decision: Manual OpenInference attrs via Telemetry port (not LangChain instrumentor)

- **Choice**: Smoke records a leaf LLM span through the port; platform may set OpenInference keys via `phoenix.otel` re-exports or plain strings. Domain port stays string-keyed.
- **Options considered**: A) Manual attrs through the port, B) Enable `openinference-instrumentation-langchain` / `auto_instrument=True` now, C) Raw GenAI semconv only.
- **Why**: Matches “auto-instrumentation deferred to **4.4**” while still producing Phoenix-friendly LLM spans; port stays framework-free.
- **Rejected because**: B — premature; C — Phoenix UI/cost path is OpenInference-first (`llm.provider`).

### Decision: `arize-phoenix-otel` (`phoenix.otel.register`) in platform bootstrap

- **Choice**: Pin lightweight **`arize-phoenix-otel` (≥0.16.0)** and call `phoenix.otel.register(...)` from `platform/telemetry` when export is enabled. Domain still only sees the `Telemetry` Protocol (hexagonal intact). Wire protocol remains OTLP; we do not hand-roll the exporter.
- **Options considered**: A) Hand-roll OTel (`OTLPSpanExporter` + Resource + processor), B) `arize-phoenix-otel` / `register()`, C) full `arize-phoenix` server SDK, D) gRPC OTLP only.
- **Why (from Phoenix docs)**:
  - Collapses Resource / exporter / processor / TracerProvider into one call with Phoenix-aware defaults.
  - Sets `openinference.project.name` from `project_name` / `PHOENIX_PROJECT*`.
  - Auto-detects HTTP vs gRPC; appends `/v1/traces`; optional `PHOENIX_API_KEY` Bearer.
  - **`batch=False` → SimpleSpanProcessor** by default (CLI smoke flush); batch is opt-in.
  - ≥0.16 re-exports OpenInference `SpanAttributes` / span-kind enums / context managers (`using_session`, etc.) for manual leaf spans.
  - `auto_instrument=True` later discovers our already-pinned LangChain OpenInference instrumentor (**4.4**) without rewriting bootstrap.
  - Upstream recommends `register()` for “single project, simple app”; raw OTel only for custom processor pipelines.
- **Rejected because**: A — reimplement footguns (path, project attr, processor choice) for no gain while Phoenix is the only collector; C — heavy server SDK, not needed (collector is already a container); D — Compose already exposes HTTP on the UI port.

### Decision: OpenRouter via `langchain-openai` `base_url` (keep for a while)

- **Choice**: `ChatOpenAI(base_url="https://openrouter.ai/api/v1", api_key=…)`; set span `llm.provider=openrouter` (not `openai`).
- **Options considered**: A) OpenRouter as the LLM hop (smoke now, reusable later), B) direct OpenAI/Anthropic adapters only, C) raw `httpx` / official OpenRouter SDK.
- **Why**: One key/bill, easy model swaps for cost/eval/o11y, OpenAI-compatible client already pinned — good default until a bakeoff forces native providers.
- **Rejected because**: B — two vendor accounts and pricing setups early; C — reinvent chat+usage or extra SDK for no gain.

### Decision: Prove “leaf LLM” offline; Phoenix e2e later

- **Choice**: Offline unit test on the smoke helper / `PhoenixTelemetry` asserts exactly one span with kind `LLM` and no parent that is also `LLM` (capture spans via a fake `Telemetry` or a test tracer provider behind the adapter — **no live Phoenix**).
- **Options considered**: A) offline span-capture unit invariant, B) required Phoenix e2e in CI, C) live OpenRouter e2e in CI.
- **Why**: Catches double-count shape without Phoenix/network flakiness; **4.6** owns end-to-end join/cost.
- **Rejected because**: B/C — need live deps; prove routing more than the leaf invariant.

### Decision: Export off = NoOpTelemetry (fail open for product paths)

- **Choice**: Unset `PHOENIX_COLLECTOR_ENDPOINT` → `NoOpTelemetry` (never call `register()`, which would default to `localhost:6006`); smoke without OpenRouter key exits non-zero with a clear message.
- **Options considered**: A) no-op when unset, B) require Phoenix always, C) raise on first span if unset.
- **Why**: Ingest/taxonomy must keep working without Phoenix; smoke is the explicit probe; avoids accidental localhost export.
- **Rejected because**: B/C — break local/CI workflows that already skip Phoenix waits.

## 8. Testing strategy

**Product decisions to protect**

- **core** — Given a `Telemetry` fake, when smoke-style code starts an LLM span and sets `llm.provider`, then those attrs are visible on the ended span record.
- **core** — Given `PHOENIX_COLLECTOR_ENDPOINT` unset, when bootstrap runs, then callers receive `NoOpTelemetry`, `register()` is not called, and `start_span`/`end` do not raise.
- **boundary** — Given `pipeline/` sources, when AST boundary test runs, then no `opentelemetry` / `phoenix` / `langchain` / `platform` adapter imports.
- **invariant** — Offline unit test: OpenRouter smoke helper emits exactly one span with `openinference.span.kind=LLM`; if a parent span exists, it must not also be `LLM` (leaf = no child LLM spans).
- **boundary** — When collector endpoint is set, bootstrap passes the Phoenix **base** URL into `register()`; path `/v1/traces` is owned by the helper.

**Unit / domain:** fakes for the Protocol; adapter/smoke tests with span capture and **no** `PHOENIX_COLLECTOR_ENDPOINT` / no network.

**Integration:** none required for Phoenix ingest in CI. Optional future: assert Phoenix accepted a span (out of scope unless cheap and reliable).

**Manual:** README steps — start Compose Phoenix → set `PHOENIX_COLLECTOR_ENDPOINT` + OpenRouter key → run smoke → open `localhost:3022` → confirm LLM span + attrs; note cost may be `$0`.

**Regression guard:** boundary tests prevent tracing SDKs leaking into `pipeline/`.

## 9. Observability

- This *is* the observability path: traces to Phoenix via `phoenix.otel.register`.
- Logs: bootstrap INFO when export enabled/disabled; ERROR on export failure without dumping secrets; smoke prints trace id to stdout.
- Metrics/alarms: N/A.
- Trace tags: leaf LLM OpenInference attrs listed in §5; optional `run_id` string attr later (**4.1** / LangGraph’s run id — not `pipeline_run_id`). Do not invent `stage_execution_id` / `llm_call_id` attrs; OTel span id covers call identity.

## 10. Rollout and rollback

- **Rollout:** merge behind normal CLI; no migration; operators opt in via `PHOENIX_COLLECTOR_ENDPOINT` (+ OpenRouter key for smoke).
- **Rollback:** revert commit; unset collector env → no-op. No data loss (traces are ephemeral in Phoenix; 30-day retention already configured).

## 11. Open questions

- Q1 — Exact default `OPENROUTER_SMOKE_MODEL` id (cheap + stable). **Non-blocking:** executor picks one documented default (e.g. a small Llama/Gemma OpenRouter slug) and makes it overridable.
- Q2 — Should `api` / `ingest` auto-call `configure_telemetry()` on startup in this PR, or only the smoke command? **Adopted recommendation:** smoke + shared bootstrap helper; call configure from `cli.main` once for all commands so later stages inherit it — still no-op without `PHOENIX_COLLECTOR_ENDPOINT`.

## 12. Hand-off block

```
HAND-OFF PROMPT
- Plan: docs/plans/20260804-backend-telemetry-port.md
- Primary packages/services: backend (pipeline ports, platform/telemetry via phoenix.otel, platform/llm OpenRouter, cli)
- Start by reading: this plan, docs/specs/architecture.md § Observability, backend/src/agentic_cataloger/taxonomy/ports.py (Protocol style), backend/tests/domain/test_catalog_boundaries.py, docs/specs/code_style_python.md §5
- Non-negotiables:
  1) No opentelemetry/phoenix/langchain imports in pipeline/ (or other domain packages)
  2) Bootstrap via phoenix.otel.register when PHOENIX_COLLECTOR_ENDPOINT set; leaf LLM span only with llm.provider=openrouter (+ model/tokens); auto_instrument=False until 4.4
  3) No live OpenRouter in default CI; unset collector endpoint ⇒ NoOpTelemetry (never call register’s localhost default)
- First concrete action: add failing domain boundary + Telemetry Protocol tests under backend/tests/domain/, then implement pipeline/ports.py
- Done when: success criteria in §3 (smoke visible in Phoenix manually; tests green offline)
```

## 13. Changelog

- 2026-08-04 — initial draft after scope lock-in
- 2026-08-04 — OpenRouter kept as lasting LLM hop (not smoke-only); clarify leaf-span = no child LLM; offline leaf invariant vs 4.6 Phoenix e2e
- 2026-08-04 — Flip bootstrap to `arize-phoenix-otel` / `phoenix.otel.register` (not hand-rolled OTLP)
- 2026-08-04 — Sweep doc language: `PhoenixTelemetry`, `PHOENIX_*` env, offline span-capture tests (drop leftover hand-rolled OTel framing)
- 2026-08-05 — Align with **4.1**/**3.1** design: future attr is `run_id` (not `pipeline_run_id`); no synthetic stage/LLM-call IDs; soft-dependency + `trace_id` handoff clarified; contracts vs pipeline port split restated
