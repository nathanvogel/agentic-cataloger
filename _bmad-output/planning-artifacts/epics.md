---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - _bmad-output/specs/spec-2026-agent-workflow/SPEC.md
  - _bmad-output/specs/spec-2026-agent-workflow/kill-pile.md
  - _bmad-output/specs/spec-2026-agent-workflow/explore-bakeoffs.md
  - _bmad-output/specs/spec-2026-agent-workflow/glossary.md
  - _bmad-output/planning-artifacts/architecture/architecture-pricecomp-2026-07-31/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/ux-designs/ux-pricecomp-2026-07-31/DESIGN.md
  - _bmad-output/planning-artifacts/ux-designs/ux-pricecomp-2026-07-31/EXPERIENCE.md
---

# pricecomp - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for pricecomp, decomposing the requirements from the SPEC (canonical contract, serving as PRD), UX Design spine pair, and Architecture spine into implementable stories.

**Note on the PRD source:** no `PRD.md` exists. `SPEC.md` is the preservation-validated canonical contract and declares itself as such; functional requirements below are derived from its capabilities (CAP-1..CAP-10), Constraints, and Non-goals, cross-checked against the Architecture spine (AD-1..AD-34).

## Requirements Inventory

### Functional Requirements

**Ingest & catalog (CAP-1, CAP-7 · AD-2, AD-6, AD-13)**

FR1: One ingest-selection primitive filters candidate products by source category or keyword; bulk is the empty filter, single is a filter of one, filtered subset is the general case — all three enter the same pipeline with no mode-specific agent path.
FR2: Source adapters supply durable source identity `(source_namespace, source_product_id, optional source_variant_id)` with `UNIQUE NULLS NOT DISTINCT` uniqueness; product name and raw/canonical URLs are mutable observations, never identity.
FR3: A source adapter without a trustworthy stable ID must explicitly defer/fail rather than silently fall back to presentation fields; identity-policy upgrades and source-namespace ownership changes require an explicit migration/alias map.
FR4: Each input belongs to an immutable catalog snapshot identified by source-observed time (UTC-interpreted), checksum, and adapter version.
FR5: Ingest replaces imported facts only for the products it observes and touches nothing else — no completeness assertion, no absence-driven deactivation, no replay-ordering equality check.
FR6: Product upsert merges LLM-extracted attributes with deterministic fields and never wipes prior LLM values; product upsert cannot write enrichment state (the D6 invariant).
FR7: Shelf price is revisioned with kind (`regular`, `promo`, `per_unit`), at most one current effective row per kind, and deterministic selection.

**Staged pipeline (CAP-2 · AD-2, AD-34)**

FR8: The pipeline runs staged discover/create → assign → extract, each stage with a separate prompt, result, and independently computable score.
FR9: Same-call category creation plus assignment is impossible by design (A1 is kill-piled).
FR10: Stage outcomes use `success`, `unknown`, `defer`, `invalid`, or `retryable_failure`, distinguish proposals from committed command receipts, carry prerequisite/produced revisions and immutable config IDs, and are the sole evaluator input.

**Substitutability taxonomy (CAP-3, CAP-8 · AD-3, AD-7, AD-17, AD-18)**

FR11: The taxonomy is one rooted parent-child tree — no cycles, no self-parenting, no graph semantics, no lateral "also-comparable" edges.
FR12: Comparison-eligible products have exactly one active leaf membership, enforced by database uniqueness and command validation; unassigned/deferred products are explicitly ineligible rather than implicitly excluded.
FR13: Consumer substitutability is defined by a prose rubric plus few-shot same/not-same labeled pairs — never by embedding clusters (S3) and never with price comparability as a membership co-criterion (S7).
FR14: Facets filter within a leaf; parents widen comparison scope only when the ancestor declares a compatible preferred comparable unit.
FR15: Import/source categories filter ingest only and are never a comparison primitive.
FR16: Assignment searches existing categories and their membership before creating; a real category is created only when none fits — no provisional/draft category state exists.
FR17: The taxonomy command surface supports merge, rename, edit, reparent (including create-parent), reassign products, flag for re-triage/HITL, and category coherence repair.
FR18: One post-bulk hygiene pass runs over the categories that run touched and demonstrates at least merge, reassign, and coherence repair; no periodic scheduled hygiene exists.
FR19: Category-affecting mutations upsert one coalesced review-request row unique per stable category scope, unioning bounded trigger facts; reassign/reparent/merge dirties old and new leaves, affected ancestry, moved subtrees, and stable source/target tombstone scopes. The hygiene pass claims and clears those rows.
FR20: No merge occurs silently from name similarity alone (M4 is kill-piled).

**Search-backed category context (CAP-6 · AD-5, AD-24)**

FR21: Agents obtain category context through search over the shared command layer; no prompt path dumps the full taxonomy or a parent subtree (C1/C5/C6 are kill-piled).
FR22: Curated MCP tools — `category search`, `category create`, `product assign`, `traits extract` — are the first capability adapter and are a thin wrapper over one command layer; no adapter may bypass commands.

**Cited traits & evidence (CAP-4 · AD-4)**

FR23: Trait/unit extraction is deterministic-first over sources `unit` → `price_text` → product name; high-confidence deterministic success skips the LLM entirely.
FR24: LLM extraction runs only for residual, low-confidence, or empty cases.
FR25: Every accepted non-null trait and quantity — deterministic or inferred — carries evidence bound to a catalog observation: source field, verbatim span, SHA-256 hash of that field's text at extraction time, and extractor/prompt version.
FR26: A deterministic validator rejects uncited non-null traits.
FR27: `unknown` and `defer` outcomes route to the DLQ rather than inventing values.

**Comparable quantities & normalized price (CAP-5 · AD-4, AD-30)**

FR28: Quantity kind distinguishes `net_content`, `item_count`, and `price_basis`; each quantity revision records qty, unit, source (`deterministic`|`inferred`), and evidence.
FR29: Quantity selection precedence is deterministic `price_basis` (when the source states a unit price and no fixed package is required), then deterministic `net_content`/`item_count`, then inferred equivalents; conflicts defer.
FR30: Compare leaves require `preferred_comparable_unit` and may declare `secondary_comparable_units[]`.
FR31: Normalized comparable price is derived on read from the current shelf-price and quantity revisions — no cache on a quantity row and no indexed comparison projection in MVP.
FR32: Results always report currency and comparable unit; mixed-currency queries fail closed.
FR33: Missing or unconvertible quantity yields null plus defer/DLQ — never a silently fabricated conversion.
FR34: Parent widening returns one result set only when the ancestor's preferred unit is compatible with descendant leaves; otherwise it returns a typed not-comparable result rather than a mixed-dimension ranking.
FR35: Normalized price is `shelf_price_amount / selected_quantity_in_preferred_unit`; a source `price_basis` converts its stated denominator directly and never invents package content. Forcing all products into a category primary unit (T3) is kill-piled.
FR36: A rare `comparable_unit_override` exists for SKUs where the leaf's preferred unit is nonsense, and is HITL-worthy only.

**Non-blocking human review (CAP-9 · AD-8, AD-13)**

FR37: A first-party Postgres `deferred_items` table stores product reference, stage, reason code, attempt count, immutable payload snapshot, trace ID/deep link, and status for `unknown`, `defer`, and low-confidence outcomes.
FR38: The pipeline completes without waiting on a human — blocking HITL (H3/H3a/H3b) and zero-HITL (H4) are kill-piled.
FR39: A first-party read-only UI lists and inspects deferred rows showing stage, reason code, payload snapshot, and a Phoenix trace deep link; reviewer domain writes are deferred.
FR40: Re-drive is a CLI command invoking the same application command handler as the pipeline.

**Evaluation & bakeoff (CAP-10 · AD-9, AD-20, AD-25, AD-31)**

FR41: Self-hosted Phoenix is the sole trace store, dataset/experiment home, and run UI; no custom agent-run trace UI (E4) is built.
FR42: E1 measures golden assignment accuracy against a versioned golden set.
FR43: E2 scores each pipeline stage independently on its own eval slice.
FR44: E3 computes average cost per item per stage as total stage cost ÷ all selected items (including defer/failure), aggregating leaf `span_kind = 'LLM'` spans only to avoid parent-span double counting.
FR45: E5 compares model and context configurations across the two provider adapters.
FR46: Two control-flow shapes (O4 explicit graph, O5 graph-of-stages with tools inside a stage) × two supply shapes (P2 one-at-a-time, P4 agent search) run inside LangGraph on the same eval set and ingest slice with shared commands, persistence, instrumentation, evals, and durability.
FR47: No control-flow or supply winner is declared before golden assignment accuracy, per-stage scores, average cost per item, speed, and inspectability results exist.
FR48: Each bakeoff candidate runs against a disposable database cloned from one immutable Postgres baseline (frozen catalog observations, taxonomy/config versions, checksum identity); candidates never share a live mutable owner database, cleanup deletes candidate databases, and a test proves no candidate can observe another's writes.

**Runtime, dispatch & durability (AD-16, AD-21, AD-22, AD-29)**

FR49: One backend image exposes `api`, `worker`, and `migrate` commands; API/MCP/CLI submit commands or durable jobs and the worker executes bulk, filtered, single-item, hygiene, re-drive, and cleanup work.
FR50: The worker acquires a PostgreSQL session-level advisory lock scoped to the application database at startup; a second worker exits with a distinct non-zero status and an explicit log line rather than starting.
FR51: PgQueuer dispatches pipeline, re-drive, maintenance, and cleanup tasks; enqueue happens after the triggering transaction commits and handlers are idempotent, so a lost enqueue is recovered by re-drive and a duplicate enqueue is a no-op.
FR52: Application work states are `pending`, `running`, `retry_wait`, `completed`, `failed`, `cancelled`; a central versioned retry policy defaults transient infrastructure failure to five exponential full-jitter attempts capped at 15 minutes; deterministic invalid/defer never infrastructure-retries; exhausted work remains inspectable and requeueable.
FR53: One immutable ingest-selection manifest groups candidate runs; each `pipeline_run_id` identifies one workflow/supply candidate and survives infrastructure retry, each stage execution gets a `stage_execution_id`, and each new provider invocation gets a `stage_attempt_id`.
FR54: Before one-time command application, the stage execution durably stores its validated outcome, request fingerprint, and config versions in application Postgres; replay reapplies that stored outcome rather than silently issuing a new provider call. Phoenix/provider IDs are supplemental provenance only.
FR55: Application idempotency is scoped by `(command_type, caller, key)`, binds a canonical payload hash, atomically records in-progress/terminal result with business effects, rejects changed payloads, and outlives queue and checkpoint replay.

**Cutover & repository structure (AD-15, AD-27, AD-28)**

FR56: Cutover provisions new databases and replays one immutable source manifest through the Python importer without legacy AI-derived state; recovery is re-import.
FR57: Legacy stays read-only and the frontend stays on the legacy API during the rebuild; no flat-taxonomy compatibility layer is added. Legacy is retired only once CAP-1–CAP-10 acceptance and the eval reports are accepted.
FR58: A reversible first bootstrap change makes `/backend` the Python monolith root, relocates the TypeScript backend and data importer under `/legacy`, fixes their paths and scripts, and updates path-scoped workspace rules and root documentation before any Python implementation begins.

### NonFunctional Requirements

**Architecture & code structure**

NFR1: The backend is a hexagonal modular monolith of vertical domain-capability packages; dependencies point inward and domain code is framework-free.
NFR2: Domain packages import no FastAPI, Pydantic, SQLAlchemy, LangGraph, LangChain, PgQueuer, Phoenix, or OpenTelemetry.
NFR3: Domain operations receive facts and return new state, rejection, and/or unpublished domain events; transactions, repositories, clocks, IDs, telemetry, and publication are application or adapter responsibilities.
NFR4: Every business operation enters exactly one application command handler and commits all required owner and idempotency writes in one Unit of Work; adapters may not compose several mutating commands to approximate one atomic operation, and no adapter, agent, graph node, or job handler touches SQL or repositories directly.
NFR5: A framework-free `contracts/v1` package owns shared values, command request/result schemas, stable domain error codes, and stage input/outcome envelopes; R/D/A workflow variants may change who produces or applies an outcome, never its schema or commit semantics.
NFR6: Every mutable concept has exactly one command owner; comparison holds no state of its own and its reads run inside one repeatable database snapshot rather than independently timed owner reads.

**Data conventions**

NFR7: Application-generated UUIDv7 is every application-owned entity's primary and public identity; `SourceIdentity` is a typed uniqueness key, not a second primary-key type; PgQueuer/LangGraph/Phoenix identifiers stay opaque adapter data mapped explicitly to application IDs.
NFR8: UTC `timestamptz` storage and RFC 3339 wire timestamps, ISO 4217 currency, a versioned canonical unit registry, positive `Decimal`/`NUMERIC(24,12)` calculation values with round-half-even only at declared presentation boundaries, string-encoded JSON decimals, and lowercase `snake_case` enums.
NFR9: Every authoritative table declares natural/current uniqueness, monotonic revision, optimistic compare-and-set behavior, and explicit supersession/history; database constraints enforce every cardinality expressible locally.
NFR10: Alembic owns application-schema migrations and never vendor tables; persistence models map explicitly to pure domain objects, and Pydantic DTOs are neither ORM nor domain entities.

**Observability**

NFR11: Domain and application own a thin telemetry port and import no OpenTelemetry package; the OTel API/SDK, `opentelemetry-exporter-otlp-proto-http`, OpenInference instrumentors, and Phoenix integration live in adapters.
NFR12: The versioned `pricecomp.telemetry.v1` convention requires `pricecomp.run.id`, `pricecomp.stage.execution_id`, `pricecomp.stage.attempt_id`, `pricecomp.item.id`, `pricecomp.category.id`, immutable prompt/workflow/supply/evaluator versions, `llm.provider`, resolved model, and token usage; native OpenInference values win where both conventions exist.
NFR13: Parent spans carry run/stage-execution scope, leaf LLM spans represent exactly one provider call, batched calls attach child/item spans or links each carrying `pricecomp.item.id`, and job envelopes propagate W3C trace context.
NFR14: Phoenix raw traces default to 30-day retention from first startup and Phoenix product telemetry is disabled; versioned datasets and experiments persist independently of trace retention.
NFR15: Cost visibility is a verified setup check, not an assumption — `llm.provider` plus a matching Settings → Models entry must resolve, and estimated cost is reconciled against provider billing for every model introduced.

**Runtime & environment**

NFR16: MVP runs a single operator against a single worker; this single-writer premise is mechanically enforced, not documented, and is what lets AD-3/AD-17/AD-21/AD-22 omit topology compare-and-set, generation watermarks, leases, and fencing tokens.
NFR17: The stack is pinned — non-free-threaded CPython 3.14.6, uv 0.12.1, PostgreSQL 18.4, LangGraph 1.2.10, langgraph-checkpoint-postgres 3.1.1, PgQueuer 1.3.2, SQLAlchemy[asyncio] 2.0.51, Alembic 1.18.5, Psycopg[binary] 3.3.4, psycopg-pool 3.3.1, FastAPI 0.141.1, FastMCP 3.4.5, Uvicorn 0.52.0, langchain-core 1.5.3, langchain-openai 1.4.1, langchain-anthropic 1.5.3, Pydantic 2.13.4, OTel API/SDK 1.44.0, OpenInference LangChain 0.1.68, Phoenix 19.11.1 — with committed `pyproject.toml` and `uv.lock`, and Linux CI against PostgreSQL 18.4 as compatibility authority. LangGraph Server/CLI extras and Pydantic V1 models are excluded; Yarn remains only for frontend and legacy TypeScript.
NFR18: Devcontainer and CI use the same role commands and PostgreSQL 18.4 image with its durable volume at `/var/lib/postgresql`; application, Phoenix, and frozen legacy use separate databases and roles; PgQueuer and LangGraph tables share the application database but remain vendor-owned.
NFR19: One-shot bootstrap order is database/role bootstrap → Alembic → PgQueuer install/upgrade → LangGraph checkpointer setup → Phoenix migration → service readiness.
NFR20: The application LLM port has LangChain chat-model adapters for exactly two providers in MVP (OpenAI and Anthropic); workflows use no LangChain agents, memory, persistence, or domain types.
NFR21: LangGraph graph state is orchestration-only and never a second business database; `AsyncPostgresSaver` uses `pipeline_run_id` as `thread_id`, a versioned workflow as checkpoint namespace, and strict MessagePack allowlisting.

**Quality, testing & scope discipline**

NFR22: Pure-domain tests require no framework or database; persistence, Unit of Work, source replay, queue, checkpoint, and migration adapters test against disposable PostgreSQL 18.4 on Linux CI.
NFR23: The D6 non-wipe regression test is mandatory.
NFR24: Crash-window and multi-writer concurrency suites are out of MVP under the single-writer premise; handler idempotency and re-drive are tested instead.
NFR25: One MCP mount/list/call smoke test plus REST contract tests cover the adapter surface; no REST↔MCP equivalence contract suite is built.
NFR26: Immutable eval manifests freeze source, taxonomy, golden-label, config, and evaluator versions plus the denominator and failure/defer treatment; stage quality, cost, and speed run as paired Phoenix dataset experiments.
NFR27: No production or experiment unit may implement or lay groundwork for any option in `kill-pile.md`; architecture and code review treat that companion as a binding negative contract.
NFR28: No prompt path may dump the full taxonomy or a parent subtree — token efficiency is a hard constraint, not an optimization.

**Scope boundaries**

NFR29: Security hardening, threat modeling, authentication, and authorization are out of scope for this initiative; API and MCP remain local or internal and no deployment exposes unauthenticated MCP mutations publicly.
NFR30: Catalog design must admit non-Swiss-grocery sources with minimal adaptation.
NFR31: Shopper-facing features (receipt upload, basket optimizer, nutrition Q&A) are out of scope for this initiative.

### Additional Requirements

**⚠️ Starter template: NONE specified.** The Architecture does not name a greenfield starter/scaffold. Instead it fixes a **Structural Seed** (directory layout) and a **mandatory reversible relocation** that must land before any Python implementation. This shapes Epic 1 Story 1.

- **Structural Seed (AD-28, Architecture §Structural Seed):** `backend/` with `pyproject.toml`, `uv.lock`, and `src/pricecomp/` packages `contracts/`, `catalog/`, `taxonomy/`, `enrichment/`, `review/`, `pipeline/`, `comparison/`, `evaluation/`, `platform/`; plus `migrations/` and `tests/{domain,integration,contract,evals}/`. `frontend/` remains the frontend root; `legacy/backend/` and `legacy/data-importer/` receive the relocated TypeScript.
- **Bootstrap acceptance manifest (gate):** bound in [`GATE-01-bootstrap.md`](../../implementation-artifacts/gates/GATE-01-bootstrap.md) — ports **`3020+n`**: API **3020**, Postgres **3021**, Phoenix **3022**, frontend **3023**; legacy frozen at **5532** / **3010**; Husky → `frontend`; legacy reference-only; root `docker-compose.yml` for new stack.
- **Database role/schema privilege manifest (gate):** bound in [`GATE-02-db-privileges.md`](../../implementation-artifacts/gates/GATE-02-db-privileges.md) — `pricecomp_app` / `pricecomp_phoenix` databases and roles, bootstrap superuser scope, schema ownership.
- **Phoenix deployment:** one container `arizephoenix/phoenix:version-19.11.1` (ELv2) in **root** `docker-compose.yml`, host port **3022** (`3020+2`) → container `6006`, pointed at `pricecomp_phoenix` via `PHOENIX_SQL_DATABASE_URL`. Legacy API is **not** required in root compose (reference-only under `legacy/`).
- **Co-hosted REST + MCP (AD-24):** one API process hosts FastAPI REST and a stateless FastMCP Streamable-HTTP ASGI app created with `http_app(path="/", stateless_http=True)` mounted at `/mcp`; FastAPI combines the MCP and application lifespans; strict trusted-host/origin settings apply whenever network-reachable.
- **Immutable effective run configuration (AD-25):** records provider, resolved model, structured-output method/schema/strictness, sampling, output limit, timeout, retry owner/count/backoff, streaming mode, and provider options. Prompt, rubric, workflow, supply strategy, evaluator, trait schema, and conversion registry carry immutable content/version identities plus optional aliases.
- **Contracts v1 inventory (AD-34):** `SourceIdentity`, `CatalogSnapshotRef`, `ProductSnapshot`, `Money`, `EvidenceRef`, typed trait/quantity values, command request/result schemas, stable domain error codes, and each stage input/outcome.
- **PgQueuer completion-reliance proof (gate):** bound in [`GATE-03-pgqueuer-proof.md`](../../implementation-artifacts/gates/GATE-03-pgqueuer-proof.md) — scenarios P1–P8 before dispatch-backed features.
- **First-party review lifecycle details (gate):** bound in [`GATE-04-review-lifecycle.md`](../../implementation-artifacts/gates/GATE-04-review-lifecycle.md) — `deferred_items` schema, open-row uniqueness, read API, CLI re-drive, `frontend/app/routes/deferred.tsx`.
- **Contract test for telemetry joins:** prove Phoenix joins E1/E2/E3/E5 without parent-token double counting.
- **Deferred-by-design gates to bind before their dependent work:** queue/checkpoint maintenance thresholds; CI/release contract (lock verification, service graph, migration gate, image build/SBOM, artifact promotion, clean-checkout smoke test); configuration and secrets contract; backup/recovery contract; operations contract (health/readiness, graceful drain, metrics, dashboards, alerts, migration-head checks, runbook ownership); frontend review and category-browser details.
- **Variant registration (AD-34 / Architecture §Deferred):** R1/R2/R5/R6 parse, D1/D2 persistence timing, and A2/A3 assignment timing variants may be evaluated only behind the fixed stage envelope, statuses, prerequisite revisions, and one-time command-application semantics; each variant must be registered before graph implementation.

**✅ AD-34 scope alignment (resolved 2026-08-01):** AD-34 amended to match the scope reduction — `EvidenceRef` is field + verbatim span + field-text hash (no byte offsets/NFC in MVP); taxonomy-wide topology compare-and-set deferred under AD-16 single-writer; per-entity optimistic revision (AD-23) remains.

### UX Design Requirements

Scope: the **pricecomp Deferred** operator surface — a single route, read-only window onto `deferred_items` (CAP-9 / FR39). Desktop-first responsive web, light mode only, English only.

**Design tokens**

UX-DR1: Implement the full color token set — `background #F7F6F3`, `surface #FFFFFF`, `surface-muted #EEF0F2`, `on-surface #1A1D21`, `on-surface-muted #5C6570`, `border #D5DAE0`, `border-strong #9AA3AD`, `primary #1F4B63`, `on-primary #FFFFFF`, `accent #C45C26`, `on-accent #FFFFFF`, `link #1F4B63`, `focus-ring #1F4B63`, and the three reason-chip pairs (`unknown #8A6D1F` on `#F5EED8`, `defer #1F4B63` on `#E4EEF3`, `low_confidence #6B4F7A` on `#EFE8F3`). Accent is reserved exclusively for the Phoenix deep link.
UX-DR2: Implement typography tokens — IBM Plex Sans (display 28px/600/1.2/-0.02em; title 18px/600/1.3; body 14px/400/1.5; label 12px/500/1.4/0.04em) and IBM Plex Mono (12px/400/1.45). Mono is used for machine values (product IDs, reason codes, stage names, trace IDs, timestamps, payload JSON); sans for human-readable product titles and chrome.
UX-DR3: Implement shape and spacing tokens — radii `sm 2px`, `md 4px`, `lg 6px`, `full 9999px`; spacing unit 8px, gutter 24px, desktop margin 32px, mobile margin 16px, content-max 1100px.

**Components**

UX-DR4: **Page shell** — `background` fill, header carrying the product name in display type plus "Deferred", an open-count in muted mono (e.g. `7 open`), and a Refresh control. No sidebar nav, no multi-page app shell, no settings surface.
UX-DR5: **Filter chip** — outline `border-strong`, active state fills `primary`/`on-primary`, label typography, `full` radius. Stage filter is single-select; reason filter is single-select; the two AND together; clearing returns to all.
UX-DR6: **Deferred row** — flat full-width row on `surface` with 1px `border` and `md` radius, laying out product name (sans) + supermarket/id (mono) · stage (mono) · reason chip · attempts · relative time · Phoenix link. Sorted newest first. The entire row expands and collapses on click or Enter and never navigates away.
UX-DR7: **Reason chip** — pill at `full` radius using label typography, colored from the reason token set, with the stored reason code string as its text. Chips on rows are display-only; only filter-bar chips filter.
UX-DR8: **Expanded detail** — opens in-row (never a modal), indented under the row on `surface-muted`, containing the read-only payload snapshot in mono, optional `evidence_span`, and the Phoenix URL. Long JSON truncates with a "Show more" that expands in place. No edit controls of any kind.
UX-DR9: **Phoenix link** — "Open trace" in `accent` with the mono `trace_id`, opening a new browser tab and stopping propagation so the row does not toggle. A missing `trace_id`/URL renders a disabled control with muted "No trace" and the row remains listed.
UX-DR10: **Empty state** — a centered short sentence with no illustration and no CTA, distinguishing globally empty ("No deferred items." plus one line noting ingest may still create them) from filtered-empty ("No items match these filters." plus a clear-filters control).

**States**

UX-DR11: Loading renders skeleton rows matching the deferred-row anatomy.
UX-DR12: Load failure renders inline "Couldn't load deferred items." plus a Retry control — not a modal, not a full-page error.
UX-DR13: Staleness is handled by the manual header Refresh control; no websocket or polling in MVP.

**Interaction & accessibility**

UX-DR14: Filter state is reflected in URL query params (`?stage=&reason=`) and a URL loaded with those params applies them — required for shareable portfolio demo links.
UX-DR15: Keyboard interaction — `j`/`k` move focus between rows, `Enter` toggles expand/collapse, `o` opens the Phoenix trace for the focused row.
UX-DR16: Accessibility floor — WCAG 2.2 AA text contrast against `background` and `surface` with the three reason-chip pairs explicitly verified; `aria-expanded` on the expand/collapse control; labeled detail region; reason and stage conveyed as text and not by color alone; focus ring using the `focus-ring` token; the external Phoenix link announcing that it opens in a new window.
UX-DR17: Responsive behavior — desktop-primary single column capped at 1100px showing the full row grid; on narrow viewports filters wrap and row metadata stacks under the product name. Web only, no native app.
UX-DR18: Motion is limited to an optional ~150ms expand transition; no celebration or attention-seeking motion.

**Content & negative constraints**

UX-DR19: Microcopy renders reason codes exactly as stored (`unknown`, `defer`, `low_confidence`) and stage names exactly as the pipeline uses them (`assign`, `extract`, …) — no euphemisms, no invented UI stage labels, no emoji status, no congratulatory copy.
UX-DR20: Banned in MVP — drag-and-drop, bulk select, inline edit, status transitions from the UI, assignment, and comments. The surface must not imply write affordances while it is read-only.
UX-DR21: Visual restraint is binding — no charts, KPI strips, or health-score widgets; no drop shadows or elevation as hierarchy; no purple/indigo AI gradients or glow; no dark mode; and Phoenix is never restyled or re-skinned, only deep-linked.

### FR Coverage Map

| FR | Epic | Coverage |
| --- | --- | --- |
| FR1 | Epic 1 | One ingest-selection primitive for bulk / single / filtered |
| FR2 | Epic 1 | Durable source identity with NULLS NOT DISTINCT uniqueness |
| FR3 | Epic 1 | Explicit defer/fail on missing stable ID; migration/alias map |
| FR4 | Epic 1 | Immutable catalog snapshot identity |
| FR5 | Epic 1 | Observed-products-only replacement semantics |
| FR6 | Epic 1 | D6 merge-never-wipe; upsert cannot write enrichment |
| FR7 | Epic 1 | Revisioned shelf price with kind and one current row per kind |
| FR8 | Epic 4 | Three separately-prompted, separately-scored stages |
| FR9 | Epic 4 | Same-call create+assign structurally impossible |
| FR10 | Epic 4 | Stage outcome envelope as sole evaluator input |
| FR11 | Epic 2 | Rooted tree; no cycles, no graph, no lateral edges |
| FR12 | Epic 2 | Exactly-one active leaf membership; explicit ineligibility |
| FR13 | Epic 2 | Rubric + few-shot pairs define substitutability |
| FR14 | Epic 2 | Facets filter within leaf; parents widen on compatible unit |
| FR15 | Epic 2 | Import/source categories filter ingest only |
| FR16 | Epic 2 | Prefer-match-before-create; no draft categories |
| FR17 | Epic 2 | Full hygiene command surface incl. coherence repair |
| FR18 | Epic 2 | Post-bulk hygiene pass over touched categories |
| FR19 | Epic 2 | Coalesced taxonomy review requests; hygiene claims/clears |
| FR20 | Epic 2 | No silent name-similarity merge |
| FR21 | Epic 2 | Search-backed category context; no taxonomy dump |
| FR22 | Epic 2 | Curated MCP tools as thin adapter over commands |
| FR23 | Epic 3 | Deterministic-first extraction; high-conf skips LLM |
| FR24 | Epic 3 | LLM extract only for residual/low-conf/empty |
| FR25 | Epic 3 | Evidence on every accepted non-null trait and quantity |
| FR26 | Epic 3 | Deterministic validator rejects uncited non-null traits |
| FR27 | Epic 3 | unknown/defer route to DLQ |
| FR28 | Epic 3 | Quantity kinds with source and evidence |
| FR29 | Epic 3 | Quantity selection precedence; conflicts defer |
| FR30 | Epic 2 | Comparable-unit policy declared on compare leaves |
| FR31 | Epic 3 | Normalized price derived on read; no cache, no projection |
| FR32 | Epic 3 | Currency + comparable unit always reported; mixed fails closed |
| FR33 | Epic 3 | Missing/unconvertible yields null + defer, never fabrication |
| FR34 | Epic 3 | Typed not-comparable result on incompatible parent widening |
| FR35 | Epic 3 | Normalization formula; price_basis converts stated denominator |
| FR36 | Epic 3 | Rare comparable_unit_override, HITL-worthy only |
| FR37 | Epic 3 | deferred_items table with payload snapshot and trace ref |
| FR38 | Epic 3 | Pipeline never blocks on a human |
| FR39 | Epic 5 | First-party read-only deferred dashboard |
| FR40 | Epic 5 | CLI re-drive through the same command handler |
| FR41 | Epic 6 | Phoenix as sole trace/dataset/experiment/run UI |
| FR42 | Epic 6 | E1 golden assignment accuracy |
| FR43 | Epic 6 | E2 per-stage scoring |
| FR44 | Epic 6 | E3 average cost per item; leaf LLM spans only |
| FR45 | Epic 6 | E5 model/context comparison |
| FR46 | Epic 6 | 2 control-flow x 2 supply on identical harness |
| FR47 | Epic 6 | No winner before full metric set exists |
| FR48 | Epic 6 | Cloned-baseline database isolation per candidate |
| FR49 | Epic 1 | One image, three role commands |
| FR50 | Epic 1 | Advisory-lock single-writer enforcement |
| FR51 | Epic 1 | PgQueuer dispatch; enqueue-after-commit; idempotent handlers |
| FR52 | Epic 1 | Work states and central versioned retry policy |
| FR53 | Epic 4 | Run / stage-execution / stage-attempt identity |
| FR54 | Epic 4 | Durable stage outcome; replay reapplies stored result |
| FR55 | Epic 1 | Application idempotency keyed by command/caller/key |
| FR56 | Epic 1 | Fresh-rebuild cutover by manifest replay |
| FR57 | Epic 1 | Legacy read-only; frontend stays on legacy API |
| FR58 | Epic 1 | Reversible bootstrap relocation before Python work |

**Coverage check:** 58 FRs, 58 mapped, 0 unassigned, 0 duplicated.

## Epic List

### Epic 1: Runnable Python Stack with Non-Destructive Catalog Ingest

An operator can boot the new Python backend — `api`, `worker`, and `migrate` roles against PostgreSQL 18.4 and self-hosted Phoenix — and pull a bulk, single, or filtered slice of source products into the new catalog through one ingest primitive, with durable job dispatch, a mechanically enforced single writer, and a proven guarantee that re-import never wipes enrichment.

**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR49, FR50, FR51, FR52, FR55, FR56, FR57, FR58

### Epic 2: Substitutability Taxonomy an Operator Curates and an Agent Searches

An operator can build and repair a rooted substitutability tree — create, merge, rename, edit, reparent, reassign, flag, and coherence-repair — with exactly-one-leaf membership enforced in the database and comparable-unit policy declared on compare leaves. Any caller, human or agent, obtains category context by search rather than a taxonomy dump.

**FRs covered:** FR11, FR12, FR13, FR14, FR15, FR16, FR17, FR18, FR19, FR20, FR21, FR22, FR30

### Epic 3: Comparison-Ready Rows — Cited Traits, Quantities, and Normalized Price

An operator can turn imported products into comparison-ready rows: structured traits and quantities where every non-null value cites verbatim source evidence, plus a normalized comparable price derived on read. Anything unknown, unconvertible, or conflicting lands in a non-blocking deferred queue instead of being invented.

**FRs covered:** FR23, FR24, FR25, FR26, FR27, FR28, FR29, FR31, FR32, FR33, FR34, FR35, FR36, FR37, FR38

### Epic 4: Staged Agent Pipeline with End-to-End Inspectable Runs

An operator can run discover/create, assign, and extract as three separately-prompted, separately-scored LangGraph stages over an ingest slice, with every run, stage execution, and provider call durably identified, replay-safe, and visible end to end in Phoenix.

**FRs covered:** FR8, FR9, FR10, FR53, FR54

### Epic 5: Deferred — Seeing Where the Agent Fails

An operator can open one read-only web surface listing every deferred item with its stage, reason code, payload snapshot, and Phoenix trace deep link, scan failure patterns by stage and reason without leaving the list, and re-drive any item by CLI.

**FRs covered:** FR39, FR40 — plus all 21 UX Design Requirements

### Epic 6: Eval Harness and the Controlled 2x2 Bakeoff

An operator can score golden assignment accuracy, per-stage quality, and average cost per item against frozen eval manifests, and run two control-flow shapes against two supply shapes on identical data in isolated databases, producing shareable metrics before any winner is declared.

**FRs covered:** FR41, FR42, FR43, FR44, FR45, FR46, FR47, FR48

### Epic Dependency Flow

```text
E1 ──┬──> E2 ──┬──> E3 ──┬──> E4 ──> E6
     │         │         │
     └─────────┴─────────┴──> E5
```

No epic requires a future epic to function. Epic 3 stands alone without any LLM because FR23 makes extraction deterministic-first, so comparison-ready rows ship for the deterministic subset before an agent exists. Epic 5 likewise ships against deterministic deferrals; Epic 4 later populates `trace_id` on the same rows.

## Epic 1: Runnable Python Stack with Non-Destructive Catalog Ingest

An operator can boot the new Python backend — `api`, `worker`, and `migrate` roles against PostgreSQL 18.4 and self-hosted Phoenix — and pull a bulk, single, or filtered slice of source products into the new catalog through one ingest primitive, with durable job dispatch, a mechanically enforced single writer, and a proven guarantee that re-import never wipes enrichment.

Covers FR1–FR7, FR49–FR52, FR55, FR56–FR58. Governed by AD-1, AD-2, AD-6, AD-13–AD-16, AD-22, AD-23, AD-26–AD-30.

### Story 1.1: Relocate Legacy TypeScript and Seed the Python Monolith

As an operator,
I want the legacy TypeScript stack moved under `/legacy` and `/backend` reseeded as the Python monolith root,
So that Python implementation can begin against the architecture's structural seed without legacy code obstructing the active tree.

**Gate:** [`GATE-01-bootstrap.md`](../../implementation-artifacts/gates/GATE-01-bootstrap.md)

**Acceptance Criteria:**

**Given** the repository before relocation
**When** the relocation change is applied per GATE-01
**Then** `legacy/backend/`, `legacy/data-importer/`, `legacy/db/`, `legacy/.kiro/`, `legacy/docker-compose.yml`, and `legacy/docs/decision_records/ADR001-llm-library-selection.md` exist
**And** `data/` and `frontend/` remain at the repo root
**And** `sync-ai-rules.sh` and `.cursor/rules/` are removed
**And** Husky `pre-commit` runs `frontend` lint-staged only

**Given** the relocation has been applied
**When** the change is reviewed
**Then** legacy is treated as reference-only until parity — **no** requirement to pass legacy build or test from CI or this story
**And** active ports follow GATE-01: API **3020**, Postgres **3021**, Phoenix **3022**, frontend **3023**; legacy frozen at **3010** / **5532**

**Given** the relocated repository
**When** `backend/` is seeded per AD-28
**Then** it contains `pyproject.toml`, `uv.lock`, and `src/pricecomp/` with empty-but-present packages `contracts/`, `catalog/`, `taxonomy/`, `enrichment/`, `review/`, `pipeline/`, `comparison/`, `evaluation/`, `platform/`
**And** `migrations/` and `tests/domain/`, `tests/integration/`, `tests/contract/`, `tests/evals/` exist
**And** no Python domain logic is included — structural seed only

**Given** the relocation and seed change
**When** it is reviewed against GATE-01
**Then** root documentation references the new layout
**And** the relocation is demonstrably reversible by inverting the moves

**Given** the pinned toolchain
**When** `uv sync` runs on the committed lockfile
**Then** it resolves against non-free-threaded CPython 3.14.6 and uv 0.12.1
**And** LangGraph Server/CLI extras and Pydantic V1 models are absent from the resolved set

### Story 1.2: Run the Stack Locally with Role Commands

As an operator,
I want one backend image exposing `api`, `worker`, and `migrate` commands alongside PostgreSQL and Phoenix via root `docker-compose.yml`,
So that I can bring the new stack up locally and in CI with identical commands.

**Gates:** [`GATE-01-bootstrap.md`](../../implementation-artifacts/gates/GATE-01-bootstrap.md), [`GATE-02-db-privileges.md`](../../implementation-artifacts/gates/GATE-02-db-privileges.md)

**Acceptance Criteria:**

**Given** the backend image
**When** it is invoked with `api`, `worker`, or `migrate`
**Then** each role starts independently from the same image
**And** no Redis or external workflow runtime is required

**Given** a clean environment
**When** the one-shot bootstrap runs
**Then** it executes in the order database/role bootstrap, Alembic, PgQueuer install/upgrade, LangGraph checkpointer setup, Phoenix migration, then service readiness
**And** each step is idempotent on re-run

**Given** root `docker compose up -d`
**When** the Compose environment is brought up
**Then** PostgreSQL 18.x runs on host port **3021** (`3020+1`) with its durable volume mounted at `/var/lib/postgresql`
**And** Phoenix runs from `arizephoenix/phoenix:version-19.11.1` on host port **3022** (`3020+2`) against `pricecomp_phoenix` via `PHOENIX_SQL_DATABASE_URL`
**And** the `api` role binds host port **3020** when started
**And** root compose references only the new Postgres instance on **3021** — no env vars, volumes, `depends_on`, or connection strings for legacy (`legacy/docker-compose.yml` / **5532** remain fully separate)

**Given** the database role and privilege manifest (GATE-02)
**When** the bootstrap provisions databases and roles
**Then** `pricecomp_app` and `pricecomp_phoenix` exist with least-privilege runtime roles per GATE-02
**And** runtime credentials cannot create databases or run arbitrary migrations
**And** PgQueuer and LangGraph tables live in the application database but remain vendor-owned with their own schemas and `search_path`

**Given** Phoenix has started for the first time
**When** its project settings are inspected
**Then** raw trace retention is set to 30 days
**And** Phoenix product telemetry is disabled

**Given** the devcontainer and CI
**When** each runs the stack
**Then** both use the same role commands and the same PostgreSQL 18.x image

### Story 1.2a: Prove PgQueuer Completion Reliance (GATE-03 Spike)

As an operator,
I want the PgQueuer completion-reliance proof to run immediately after the local stack works and before catalog ingest begins,
So that queue selection is confirmed or reopened before Stories 1.4–1.9 assume AD-22.

**Gate:** [`GATE-03-pgqueuer-proof.md`](../../implementation-artifacts/gates/GATE-03-pgqueuer-proof.md)

**Sequencing note (TECH-001):** This spike was pulled forward from Story 1.10. Story 1.3 may proceed in parallel. Stories **1.4+** are blocked until P1–P8 are green or the Architect reopens queue selection. Story 1.10 keeps production dispatch and central retry policy ACs and reuses this suite as regression.

**Acceptance Criteria:**

**Given** Story 1.2 has delivered role commands, migrate, and disposable PostgreSQL 18.4
**When** `backend/tests/integration/test_pgqueuer_reliance.py` runs on Linux CI
**Then** GATE-03 scenarios P1–P8 all pass on a single worker
**And** the fixture surface is platform-only (no catalog domain tables)
**And** enqueue remains after commit (no transaction-joining producer bridge)

**Given** any of P1–P8 cannot be satisfied with PgQueuer 1.3.2
**When** the spike concludes
**Then** AD-22 queue selection is reopened with the Architect before Story 1.4 starts

### Story 1.3: Enforce the Single Writer at Worker Startup

As an operator,
I want a second worker to fail at boot rather than start,
So that accidental concurrency cannot silently corrupt taxonomy topology or poison eval baselines.

**Acceptance Criteria:**

**Given** no worker is running
**When** a worker starts
**Then** it acquires a PostgreSQL session-level advisory lock scoped to the application database
**And** it proceeds to serve work

**Given** a worker already holds the advisory lock
**When** a second worker starts
**Then** it does not begin processing any work
**And** it exits with a distinct non-zero status code reserved for this condition
**And** it emits an explicit log line naming the single-writer constraint as the cause

**Given** a running worker
**When** its process terminates for any reason
**Then** the session-level lock is released by the database
**And** a subsequent worker starts successfully

**Given** a rolling deploy or a two-replica default
**When** it would place two workers concurrently
**Then** the second fails to boot rather than starting alongside the first

**Given** bakeoff candidates each holding their own database
**When** they run concurrently
**Then** the guard does not prevent them, because the lock is scoped per application database

### Story 1.4: Register an Immutable Catalog Snapshot

As an operator,
I want every batch of source input recorded as an immutable, identified snapshot,
So that any import can be traced to exactly the observation set it came from and replayed deterministically.

**Acceptance Criteria:**

**Given** a source input batch
**When** it is registered
**Then** a catalog snapshot row is created carrying source-observed time interpreted as UTC, a checksum over the input, and the adapter version
**And** its identity is an application-generated UUIDv7

**Given** a registered catalog snapshot
**When** any attempt is made to modify its identifying fields
**Then** the modification is rejected
**And** the existing row is unchanged

**Given** the same input batch registered twice with the same checksum and adapter version
**When** the second registration runs
**Then** it resolves to the existing snapshot rather than creating a duplicate

**Given** a snapshot registration
**When** the snapshot is persisted
**Then** the write occurs inside one Unit of Work through a single application command handler
**And** no adapter reaches the repository or SQL directly

### Story 1.5: Import Products Under Durable Source Identity

As an operator,
I want products keyed by a stable source identity rather than by name or URL,
So that re-imports match the same product even when its presentation fields change.

**Acceptance Criteria:**

**Given** a source adapter supplying `(source_namespace, source_product_id, optional source_variant_id)`
**When** products are imported from a snapshot
**Then** each catalog product is keyed by that triple with `UNIQUE NULLS NOT DISTINCT` uniqueness
**And** the product carries a UUIDv7 application identity distinct from its source identity

**Given** a product whose name or canonical/raw URL changed since the previous snapshot
**When** it is re-imported under the same source identity
**Then** it resolves to the same catalog product
**And** the changed name and URLs are recorded as new mutable observations rather than as identity

**Given** a source record with a missing or untrustworthy stable ID
**When** the adapter processes it
**Then** the adapter explicitly defers or fails that record
**And** it never falls back to a presentation field such as name or URL to synthesise identity

**Given** two source records colliding on the same source identity within one snapshot
**When** they are imported
**Then** the collision is reported explicitly rather than silently resolved

**Given** a source namespace whose ownership or identity policy must change
**When** the change is applied
**Then** it requires an explicit migration or alias map
**And** the import path refuses to change identity silently

**Given** each source adapter
**When** its normalization behavior is inspected
**Then** it declares a versioned normalization policy recorded with the import

### Story 1.6: Select What to Ingest — Bulk, Single, or Filtered

As an operator,
I want one selection primitive that filters by source category or keyword,
So that bulk, single-product, and filtered subset ingest all run the same code path.

**Acceptance Criteria:**

**Given** the ingest selection primitive
**When** it is invoked with an empty filter
**Then** it selects the whole snapshot as a bulk ingest

**Given** the ingest selection primitive
**When** it is invoked with a filter matching exactly one product
**Then** it performs a single-product ingest through the identical code path used by bulk

**Given** the ingest selection primitive
**When** it is invoked with a source category or keyword filter
**Then** it selects the matching subset
**And** the resulting selection is recorded as an immutable ingest-selection manifest

**Given** the three invocation shapes
**When** their execution paths are compared
**Then** no mode-specific branch exists in the ingest or downstream agent path

**Given** an ingest run over a selection
**When** it completes
**Then** imported facts are replaced only for the products the run observed
**And** products absent from the selection are untouched, with no deactivation and no completeness assertion recorded

### Story 1.7: Record Revisioned Shelf Prices

As an operator,
I want shelf prices stored as typed revisions with exactly one current row per kind,
So that price history is preserved and price selection for comparison is deterministic.

**Acceptance Criteria:**

**Given** a product observation carrying a price
**When** the price is recorded
**Then** it is stored as a shelf-price revision with kind `regular`, `promo`, or `per_unit`
**And** it carries an ISO 4217 currency and a `NUMERIC(24,12)` positive Decimal amount

**Given** an existing current shelf price of a given kind
**When** a newer revision of that same kind is recorded
**Then** the prior row is explicitly superseded
**And** at most one current effective row exists per kind, enforced by a database constraint

**Given** several current shelf-price kinds for one product
**When** a price is selected for downstream use
**Then** selection follows a single deterministic rule
**And** the same inputs always yield the same selected price

**Given** a shelf price stored and read back
**When** its amount is serialised to JSON
**Then** the decimal is string-encoded rather than emitted as a float

### Story 1.8: Guarantee Re-Import Never Wipes Enrichment

As an operator,
I want catalog upsert structurally unable to touch enrichment-owned state,
So that re-importing a product preserves previously extracted LLM attributes — the D6 bug cannot recur.

**Acceptance Criteria:**

**Given** no enrichment-owned storage exists yet
**When** this story is implemented
**Then** it creates the minimal enrichment-owned product attribute revision table required to express and test the ownership boundary, and nothing more
**And** Epic 3 extends that table with trait typing, evidence, and quantity revisions rather than replacing it

**Given** the ownership split between catalog and enrichment
**When** the catalog upsert command is inspected
**Then** its writable set contains only catalog-owned tables and columns
**And** it has no code path, repository, or column mapping reaching enrichment-owned state

**Given** a product carrying enrichment-owned attribute values
**When** the same product is re-imported from a newer snapshot
**Then** every enrichment-owned value is unchanged after the import
**And** deterministic catalog-owned fields are updated from the new observation

**Given** the mandatory D6 regression test
**When** the test suite runs
**Then** the test seeds enrichment-owned attributes, performs a full re-import, and asserts non-wipe
**And** the test fails if the upsert is ever widened to write enrichment state

**Given** an attempt to write an enrichment-owned value through the import path
**When** it is executed
**Then** it is rejected rather than silently applied

### Story 1.9: Make Commands Idempotent Under Replay

As an operator,
I want every business command to carry an idempotency contract,
So that a retried or replayed command applies its effects exactly once.

**Acceptance Criteria:**

**Given** a command invocation
**When** it is submitted with `(command_type, caller, key)`
**Then** the idempotency record is scoped by that triple
**And** it binds a canonical hash of the request payload

**Given** an in-progress command with a given idempotency triple
**When** the same triple is submitted again
**Then** the in-progress state is observed rather than a second execution starting

**Given** a terminal command result
**When** the same idempotency triple is resubmitted with an identical payload
**Then** the stored terminal result is returned
**And** no business effect is applied a second time

**Given** a terminal command result
**When** the same idempotency triple is resubmitted with a changed payload
**Then** the request is rejected with a stable domain error code

**Given** an idempotency record
**When** the queue or a checkpoint replays the work that produced it
**Then** the record still resolves, because its lifetime exceeds queue and checkpoint retention

**Given** a command that commits business effects
**When** it completes
**Then** the idempotency record and the business effects commit in the same Unit of Work

### Story 1.10: Dispatch Durable Work with a Central Retry Policy

As an operator,
I want ingest and maintenance work dispatched durably with predictable retry behavior,
So that long-running work survives restarts without coupling it to API availability.

**Acceptance Criteria:**

**Given** a command that triggers durable work
**When** the triggering transaction commits
**Then** the PgQueuer enqueue happens after that commit
**And** no transaction-joining producer bridge is used

**Given** an enqueue that is lost because the process died between commit and enqueue
**When** the owner row is inspected
**Then** the work is recoverable by re-driving from that row

**Given** a duplicated enqueue of the same work
**When** the handler executes twice
**Then** the second execution is a no-op because the handler is idempotent

**Given** any unit of application work
**When** its state is inspected
**Then** it is one of `pending`, `running`, `retry_wait`, `completed`, `failed`, or `cancelled`

**Given** a transient infrastructure failure
**When** the central versioned retry policy applies
**Then** it retries up to five times with exponential full jitter capped at 15 minutes

**Given** a deterministic `invalid` or `defer` outcome
**When** it is returned
**Then** no infrastructure retry occurs

**Given** work that has exhausted its retries
**When** an operator inspects it
**Then** the work remains visible and can be requeued

**Given** the completion-reliance proof required before dispatch-backed features (GATE-03)
**When** it is executed on a single worker
**Then** scenarios P1–P8 in [`GATE-03-pgqueuer-proof.md`](../../implementation-artifacts/gates/GATE-03-pgqueuer-proof.md) pass in `backend/tests/integration/test_pgqueuer_reliance.py`
**And** if Story 1.2a already proved P1–P8, this story treats that suite as regression while landing production dispatch and the central retry policy

### Story 1.11: Rebuild the Catalog from an Immutable Source Manifest

As an operator,
I want cutover to be a fresh rebuild replayed from one immutable manifest,
So that recovery is simply re-import and no legacy AI-derived state contaminates the new system.

**Acceptance Criteria:**

**Given** newly provisioned application databases
**When** the cutover replay runs
**Then** one immutable source manifest is replayed through the Python importer
**And** no legacy AI-derived category or attribute state is carried across

**Given** the rebuild is in progress
**When** the legacy system is accessed
**Then** legacy is read-only
**And** the frontend continues to consume the legacy API

**Given** the rebuilt system
**When** its taxonomy surface is inspected
**Then** no flat-taxonomy compatibility layer exists for legacy consumers

**Given** a rebuilt database that must be recovered
**When** recovery is performed
**Then** it is achieved by re-running the manifest replay
**And** no freeze/restore drill, reconciliation gate, observation window, or routing-rollback rehearsal is required

**Given** the same manifest replayed twice into fresh databases
**When** the resulting catalog state is compared
**Then** the two results are equivalent

## Epic 2: Substitutability Taxonomy an Operator Curates and an Agent Searches

An operator can build and repair a rooted substitutability tree — create, merge, rename, edit, reparent, reassign, flag, and coherence-repair — with exactly-one-leaf membership enforced in the database and comparable-unit policy declared on compare leaves. Any caller, human or agent, obtains category context by search rather than a taxonomy dump.

Covers FR11–FR22 and FR30. Governed by AD-3, AD-5, AD-7, AD-13, AD-14, AD-17, AD-18, AD-24.

### Story 2.1: Build a Rooted Substitutability Tree

As an operator,
I want substitutability categories stored as one rooted parent-child tree,
So that comparison scope is unambiguous and cannot degrade into graph semantics.

**Acceptance Criteria:**

**Given** the taxonomy is empty
**When** categories are created
**Then** they form one rooted parent-child tree with each non-root category having exactly one parent
**And** each category carries a UUIDv7 application identity

**Given** an existing category
**When** a command attempts to set that category as its own parent
**Then** the command is rejected with a stable domain error code

**Given** an existing ancestor chain
**When** a command attempts a reparent that would create a cycle
**Then** the command is rejected and the tree is unchanged

**Given** the taxonomy command surface
**When** it is inspected for lateral relationships
**Then** no "also-comparable" or cross-branch edge type exists
**And** no graph adjacency structure is present

**Given** any taxonomy mutation
**When** it is applied
**Then** it enters a single application command handler and commits in one Unit of Work

### Story 2.2: Declare Comparable-Unit Policy on Compare Leaves

As an operator,
I want each compare leaf to declare its preferred comparable unit,
So that downstream basket math has an unambiguous denominator for that leaf.

**Acceptance Criteria:**

**Given** a category intended for default comparison
**When** it is created or promoted to a compare leaf
**Then** `preferred_comparable_unit` is required and is rejected if absent

**Given** a compare leaf
**When** `secondary_comparable_units` is supplied
**Then** it is stored as an optional list
**And** every entry resolves against the versioned canonical unit registry

**Given** a proposed comparable unit that does not resolve in the canonical unit registry
**When** it is submitted
**Then** the command is rejected rather than storing an unrecognised unit string

**Given** a category's comparable-unit policy
**When** it is changed
**Then** the change is recorded as a new revision with explicit supersession

**Given** the ownership split
**When** comparable-unit policy is written
**Then** it is written only by taxonomy commands, never by enrichment or comparison

### Story 2.3: Assign a Product to Exactly One Leaf

As an operator,
I want each comparison-eligible product to hold exactly one active leaf membership,
So that a product never appears in two competing comparison sets.

**Acceptance Criteria:**

**Given** an unassigned product
**When** it is assigned to a leaf category
**Then** one active membership row links the product to that leaf
**And** database uniqueness prevents a second active membership for the same product

**Given** a product with an active leaf membership
**When** it is assigned to a different leaf
**Then** the prior membership is explicitly superseded rather than deleted
**And** exactly one active membership remains

**Given** a command attempting to assign a product to a non-leaf category
**When** it is executed
**Then** it is rejected with a stable domain error code

**Given** a product with no active membership or a deferred assignment
**When** comparison eligibility is evaluated
**Then** the product is explicitly ineligible rather than implicitly absent
**And** the ineligibility reason is inspectable

**Given** membership history
**When** it is queried
**Then** superseded memberships remain readable with their revision ordering intact

### Story 2.4: Define Substitutability by Rubric and Labeled Pairs

As an operator,
I want consumer substitutability defined by a versioned prose rubric plus few-shot same/not-same pairs,
So that category boundaries follow a stated, reviewable standard rather than an opaque signal.

**Acceptance Criteria:**

**Given** the substitutability definition
**When** it is stored
**Then** it comprises a prose rubric and a set of labeled same/not-same product pairs
**And** both carry an immutable content identity and version

**Given** the rubric and pairs
**When** a new version is published
**Then** the prior version remains retrievable by its immutable identity
**And** an optional alias may point at the current version

**Given** the substitutability definition
**When** its inputs are inspected
**Then** no embedding cluster is used as the definition of a category
**And** price comparability is not used as a membership co-criterion

**Given** the rule of thumb for granularity
**When** it is encoded in the rubric
**Then** it states that a separate leaf applies when shoppers would not silently swap, a facet applies within the same class, and a parent applies only to widen scope
**And** SKU-fine, department-coarse, and price-variance-adaptive granularity are explicitly excluded

### Story 2.5: Filter Within a Leaf Using Facets

As an operator,
I want preference filters expressed as facets on a leaf,
So that variations like organic or fat percentage refine a comparison set without fragmenting the tree.

**Acceptance Criteria:**

**Given** a leaf category
**When** a facet definition is added
**Then** it is stored as a within-leaf filter dimension owned by taxonomy
**And** adding it creates no new leaf

**Given** products in one leaf carrying facet values
**When** a facet filter is applied
**Then** the returned set is a subset of that leaf's members
**And** the set never draws members from another leaf

**Given** a facet
**When** an attempt is made to use it as a comparison primitive
**Then** the operation is rejected, because facets filter and do not define comparison scope

**Given** a facet definition
**When** it is changed
**Then** the change is a new revision with explicit supersession

### Story 2.6: Gate Parent Widening on Compatible Comparable Units

As an operator,
I want an ancestor to be usable for widening only when it declares a compatible preferred unit,
So that widening never silently mixes incompatible dimensions.

**Acceptance Criteria:**

**Given** an ancestor category and its descendant leaves
**When** widening eligibility is evaluated
**Then** the ancestor is eligible only if it declares a preferred comparable unit compatible with those descendant leaves

**Given** an ancestor whose preferred unit is incompatible with one or more descendant leaves
**When** widening eligibility is evaluated
**Then** the ancestor is reported ineligible with the incompatible descendants named

**Given** an ancestor that declares no preferred comparable unit
**When** widening eligibility is evaluated
**Then** it is ineligible for widening

**Given** an eligible ancestor such as `cow milk` over `fresh` and `UHT` leaves
**When** eligibility is evaluated
**Then** it is reported eligible and the compatible unit is returned

### Story 2.7: Keep Import Categories as Ingest Filters Only

As an operator,
I want retailer and CSV category labels usable only for filtering ingest,
So that a retailer's taxonomy can never become the comparison primitive.

**Acceptance Criteria:**

**Given** imported source category labels
**When** they are stored
**Then** they are held as catalog-owned observation data, separate from the substitutability tree

**Given** an ingest selection
**When** it filters by source category
**Then** the filter resolves against import categories

**Given** a comparison query
**When** it is constructed
**Then** it cannot be scoped by an import category
**And** any attempt to do so is rejected

**Given** the substitutability tree
**When** its provenance is inspected
**Then** no category node is created automatically from a source category label

### Story 2.8: Search the Taxonomy for Category Context

As an operator or agent,
I want to find relevant categories by search,
So that category context is obtained without dumping the taxonomy into a prompt.

**Acceptance Criteria:**

**Given** a populated taxonomy
**When** a search query is issued
**Then** a bounded, ranked set of matching categories is returned
**And** each result carries enough context to judge fit, including path and preferred comparable unit

**Given** a search result set
**When** its size is inspected
**Then** it is bounded by an explicit limit rather than returning the full tree

**Given** any prompt-facing category context path
**When** it is inspected
**Then** no path returns the full taxonomy and no path returns an entire parent subtree

**Given** a search that matches nothing
**When** it returns
**Then** it returns an explicit empty result rather than falling back to a broad dump

**Given** the search query
**When** it is executed
**Then** it runs through the shared query layer used by every adapter

### Story 2.9: Expose Curated Taxonomy Tools Over the Command Layer

As an agent,
I want curated MCP tools for category search, category create, and product assign,
So that I can reach the domain through the same commands a human uses.

**Acceptance Criteria:**

**Given** the API process
**When** it starts
**Then** it hosts FastAPI REST and a stateless FastMCP Streamable-HTTP ASGI app created with `http_app(path="/", stateless_http=True)` mounted at `/mcp`
**And** FastAPI combines the MCP and application lifespans

**Given** the MCP surface
**When** its tools are listed
**Then** `category search`, `category create`, and `product assign` are present as curated tools
**And** no tool is generated from OpenAPI

**Given** an MCP tool invocation
**When** it executes
**Then** it calls the same application command or query as the REST route
**And** it produces the same result and error contract, idempotency semantics, and telemetry

**Given** the adapter surface
**When** it is tested
**Then** one lifespan-backed initialize/list/call smoke test covers the mount
**And** no REST-to-MCP equivalence contract suite is built

**Given** the API is network-reachable
**When** it starts
**Then** strict trusted-host and origin settings are applied
**And** the surface remains local or internal only

### Story 2.10: Prefer Matching an Existing Category Before Creating

As an operator,
I want assignment to search existing categories and their membership before creating a new one,
So that the taxonomy does not fragment into near-duplicate leaves.

**Acceptance Criteria:**

**Given** a product needing a category
**When** the assignment command runs
**Then** it first searches existing categories and inspects their current membership
**And** the considered candidates are recorded on the outcome

**Given** a search that yields an adequate match
**When** assignment proceeds
**Then** the product is assigned to the existing category and no new category is created

**Given** a search that yields no adequate match
**When** assignment proceeds
**Then** a real category is created immediately
**And** no provisional, draft, or unpublished category state is written

**Given** two categories with similar names
**When** a merge is considered
**Then** no merge occurs from name similarity alone
**And** a merge requires an explicit command carrying its justification

**Given** the category model
**When** it is inspected for lifecycle states
**Then** no draft or publish transition exists

### Story 2.11: Repair the Taxonomy with Hygiene Commands

As an operator,
I want a full hygiene command surface over the taxonomy,
So that I can fix fragmentation, bad assignments, and incoherent leaves after the fact.

**Acceptance Criteria:**

**Given** the taxonomy command surface
**When** it is enumerated
**Then** it supports merge, rename, edit, reparent including create-parent, reassign products, flag for re-triage, and category coherence repair

**Given** two categories to merge
**When** the merge command runs
**Then** members move to the surviving category, the source is tombstoned with a stable identity, and existing memberships remain exactly one per product

**Given** a subtree to reparent
**When** the reparent command runs
**Then** the whole subtree moves, no cycle is created, and ancestry is recomputed

**Given** a leaf whose members include products that do not belong
**When** coherence repair runs
**Then** the offending members are reassigned or flagged
**And** the action taken is recorded per product

**Given** any hygiene command
**When** it executes
**Then** it enters one application command handler and commits in a single Unit of Work
**And** an adapter cannot approximate it by composing several mutating commands

### Story 2.12: Coalesce Taxonomy Review Requests

As an operator,
I want category-affecting mutations to accumulate into one review row per category scope,
So that hygiene has a bounded work list without a domain-event journal.

**Acceptance Criteria:**

**Given** a category-affecting mutation
**When** it commits
**Then** one review-request row is upserted, unique per stable category scope
**And** bounded trigger facts are unioned into the existing row rather than appended without limit

**Given** a reassign, reparent, or merge
**When** it commits
**Then** the old and new leaves, affected ancestry, moved subtrees, and stable source and target tombstone scopes are all marked dirty
**And** marking them does not cascade existing pending work away

**Given** repeated mutations affecting one category
**When** they commit
**Then** exactly one open review-request row exists for that scope

**Given** the review-request row
**When** it is inspected
**Then** it carries concise trigger facts and Phoenix run and trace references
**And** no domain-event outbox or journal backs it

**Given** the single-writer runtime
**When** review requests are written
**Then** no generation watermark and no fencing token is required

### Story 2.13: Run Post-Bulk Hygiene Over Touched Categories

As an operator,
I want one hygiene pass after a bulk run covering only the categories that run touched,
So that taxonomy drift is corrected without a scheduled background job.

**Acceptance Criteria:**

**Given** a completed bulk ingest run
**When** the post-bulk hygiene pass is dispatched
**Then** it processes only the categories that run touched, as identified by the open review-request rows

**Given** the hygiene pass is running
**When** it handles a review-request row
**Then** it claims the row, performs the repairs, and clears it on success

**Given** a hygiene pass over a run that produced fragmentation and bad assignments
**When** it completes
**Then** it demonstrably performed at least one merge, one reassign, and one coherence repair
**And** each action is inspectable with its target and justification

**Given** the system at rest between runs
**When** scheduling is inspected
**Then** no periodic or cron-driven hygiene job exists

**Given** a hygiene pass that fails partway
**When** it is re-driven
**Then** unclaimed and uncleared review-request rows remain available and the pass is safe to replay

## Epic 3: Comparison-Ready Rows — Cited Traits, Quantities, and Normalized Price

An operator can turn imported products into comparison-ready rows: structured traits and quantities where every non-null value cites verbatim source evidence, plus a normalized comparable price derived on read. Anything unknown, unconvertible, or conflicting lands in a non-blocking deferred queue instead of being invented.

Covers FR23–FR29 and FR31–FR38. Governed by AD-4, AD-8, AD-13, AD-25, AD-30, AD-34.

### Story 3.1: Record Deferred Items Without Blocking the Pipeline

As an operator,
I want every unknown, defer, and low-confidence outcome captured in a durable queue,
So that the pipeline finishes without waiting on me and I still have a record of what it refused to decide.

**Gate:** [`GATE-04-review-lifecycle.md`](../../implementation-artifacts/gates/GATE-04-review-lifecycle.md)

**Acceptance Criteria:**

**Given** a stage produces an `unknown`, `defer`, or low-confidence outcome
**When** the outcome is handled
**Then** a `deferred_items` row is written per GATE-04 carrying product reference, stage, reason code, attempt count, immutable payload snapshot, trace ID with deep link, and status
**And** the row carries a UUIDv7 identity

**Given** a deferred item has been written
**When** the pipeline continues
**Then** it proceeds to the next item without waiting for any human action
**And** the run reaches a terminal state regardless of how many items deferred

**Given** a stored payload snapshot
**When** any later process runs
**Then** the snapshot is immutable and reflects the state at the moment of deferral

**Given** the review package
**When** its ownership is inspected
**Then** it exclusively owns `deferred_items` writes
**And** no other package mutates those rows

**Given** the same item deferring again on a re-drive
**When** the row is updated
**Then** the attempt count increases rather than creating a duplicate open row

### Story 3.2: Extract Traits and Units Deterministically First

As an operator,
I want deterministic parsing attempted before any model call,
So that easy extractions cost no tokens at all.

**Acceptance Criteria:**

**Given** a product observation
**When** deterministic extraction runs
**Then** it attempts sources in the order `unit`, then `price_text`, then product name
**And** the source that produced each value is recorded

**Given** deterministic extraction succeeds with high confidence
**When** the extract stage continues
**Then** no LLM call is made for that value
**And** the skip is recorded on the stage outcome

**Given** deterministic extraction yields a low-confidence or empty result
**When** the extract stage continues
**Then** the value is marked as a residual eligible for LLM extraction

**Given** known parser gaps such as bare unit words, alternate count vocabulary, and a `(qty unit)` pattern inside `price_text`
**When** deterministic extraction runs against fixtures covering them
**Then** each is parsed deterministically without a model call

**Given** the extractor
**When** its version is inspected
**Then** it carries an immutable extractor version recorded with every value it produces

### Story 3.3: Cite Every Non-Null Trait with Verbatim Evidence

As an operator,
I want each accepted trait bound to the exact source text that supports it,
So that no structured value can be traced back to nothing.

**Acceptance Criteria:**

**Given** an accepted non-null trait, deterministic or inferred
**When** it is persisted
**Then** it carries evidence naming the source field, the verbatim substring, a SHA-256 hash of that field's text at extraction time, and the extractor or prompt version
**And** the evidence is bound to a specific catalog observation

**Given** a proposed non-null trait with no evidence
**When** the deterministic validator runs
**Then** the trait is rejected and never persisted

**Given** a proposed trait whose cited substring does not occur verbatim in the named source field
**When** the validator runs
**Then** the trait is rejected

**Given** a stored evidence hash
**When** it is recomputed from the named field's text
**Then** the values match

**Given** the MVP evidence shape
**When** it is inspected
**Then** it uses field, verbatim span, and field-text hash
**And** byte-offset addressing and NFC normalization guarantees are absent, per the 2026-08-01 scope reduction

**Given** traits are persisted
**When** ownership is inspected
**Then** they are written as enrichment-owned revisions, never by the catalog import path

### Story 3.4: Record Quantities with Kind, Source, and Evidence

As an operator,
I want quantities stored as typed, evidenced revisions,
So that comparable-price math has an auditable denominator.

**Acceptance Criteria:**

**Given** a quantity extracted from a product
**When** it is persisted
**Then** it records kind `net_content`, `item_count`, or `price_basis`, a positive `NUMERIC(24,12)` quantity, a unit resolving in the canonical unit registry, source `deterministic` or `inferred`, and evidence

**Given** a quantity revision
**When** a newer revision supersedes it
**Then** supersession is explicit and history remains readable

**Given** a quantity whose unit does not resolve in the canonical unit registry
**When** it is submitted
**Then** it is rejected rather than stored with an unrecognised unit

**Given** any quantity row
**When** it is inspected for a cached normalized price
**Then** no normalized-price column exists on it

**Given** an inferred quantity
**When** it is stored
**Then** it is distinguishable from a deterministic one by its source field

### Story 3.5: Select the Quantity to Compare With

As an operator,
I want a deterministic precedence rule choosing among a product's quantities,
So that the same product always compares on the same basis.

**Acceptance Criteria:**

**Given** a product with several accepted quantities
**When** selection runs
**Then** precedence is deterministic `price_basis` where the source states a unit price and no fixed package is required, then deterministic `net_content` or `item_count`, then inferred equivalents

**Given** the same product and revisions
**When** selection runs repeatedly
**Then** it returns the same quantity every time

**Given** two quantities of equal precedence that disagree
**When** selection runs
**Then** the conflict defers rather than picking one
**And** a deferred item is recorded with the conflicting candidates in its payload

**Given** a leaf declaring a preferred comparable unit
**When** selection runs
**Then** it prefers the accepted quantity matching that preferred unit

**Given** a widening query against an eligible ancestor
**When** selection runs
**Then** it matches the ancestor's preferred unit instead of the leaf's

### Story 3.6: Call an LLM Through a Provider-Agnostic Port

As an operator,
I want model calls to run through an application port with exactly two provider adapters,
So that provider differences and hidden defaults cannot confound later experiments.

**Acceptance Criteria:**

**Given** the application LLM port
**When** its adapters are enumerated
**Then** exactly two exist for MVP, backed by `langchain-openai` and `langchain-anthropic`
**And** no third provider adapter is present

**Given** a workflow using the LLM port
**When** its imports are inspected
**Then** no LangChain agent, memory, persistence, or domain type is used
**And** domain packages import no LangChain package at all

**Given** an LLM invocation
**When** it executes
**Then** an immutable effective run configuration records provider, resolved model, structured-output method, schema and strictness, sampling, output limit, timeout, retry owner, count and backoff, streaming mode, and provider options

**Given** a prompt, rubric, trait schema, or conversion registry used by a call
**When** it is referenced
**Then** it resolves by immutable content identity and version
**And** an optional alias may point at the current version

**Given** the same effective run configuration and inputs
**When** the call is replayed
**Then** the recorded configuration is sufficient to reconstruct exactly what was requested

### Story 3.7: Extract Residual Traits with the LLM, Citing or Deferring

As an operator,
I want the model to fill only what deterministic parsing could not, and to defer rather than guess,
So that model spend targets the hard cases and no value is fabricated.

**Acceptance Criteria:**

**Given** a product with residual, low-confidence, or empty values
**When** the LLM extract stage runs
**Then** it is invoked only for those values
**And** values already resolved deterministically with high confidence are not re-verified

**Given** the LLM proposes a non-null trait
**When** the outcome is validated
**Then** it must carry an `evidence_span` naming the source field and a verbatim substring
**And** an uncited proposal is rejected by the same deterministic validator used for deterministic values

**Given** the LLM cannot support a value from the source
**When** it responds
**Then** it returns `unknown` or `defer`
**And** a deferred item is recorded with the stage, reason code, and payload snapshot

**Given** the MCP surface
**When** its tools are listed
**Then** `traits extract` is present as a curated tool over the same application command

**Given** an LLM extraction outcome
**When** it is persisted
**Then** the prompt version used is recorded alongside the evidence

### Story 3.8: Derive Normalized Comparable Price on Read

As an operator,
I want normalized comparable price computed at query time from current revisions,
So that no cache or projection can drift away from the underlying price and quantity.

**Acceptance Criteria:**

**Given** a product with a current shelf price and a selected quantity
**When** a comparison query runs
**Then** normalized price is computed as `shelf_price_amount / selected_quantity_in_preferred_unit`
**And** the computation uses positive `NUMERIC(24,12)` Decimals with round-half-even applied only at the declared presentation boundary

**Given** a source-stated `price_basis`
**When** normalization runs
**Then** the stated denominator is converted directly
**And** no package content is invented to reach the preferred unit

**Given** the persisted schema
**When** it is inspected
**Then** no normalized-price cache exists on any quantity row
**And** no indexed comparison projection table exists

**Given** a shelf price or quantity revision changes
**When** the comparison query is re-run
**Then** the returned normalized price reflects the new current revisions with no invalidation step

**Given** a comparison query returning several products
**When** it executes
**Then** all owner reads occur inside one repeatable database snapshot rather than independently timed reads

### Story 3.9: Report Currency and Unit, and Fail Closed Instead of Fabricating

As an operator,
I want every comparison result to state its currency and comparable unit, and to refuse rather than fake a conversion,
So that a number on screen is never quietly meaningless.

**Acceptance Criteria:**

**Given** any comparison result
**When** it is returned
**Then** it carries its ISO 4217 currency and its comparable unit
**And** decimals are string-encoded in JSON

**Given** a comparison query spanning more than one currency
**When** it executes
**Then** it fails closed with a stable domain error code
**And** no implicit currency conversion is applied

**Given** a product with no selectable quantity
**When** its normalized price is requested
**Then** the result is null rather than an estimate
**And** a deferred item is recorded

**Given** a product whose selected quantity cannot be converted to the preferred comparable unit
**When** normalization runs
**Then** the result is null, a deferred item is recorded, and no conversion is invented

**Given** the conversion registry
**When** a conversion is attempted
**Then** it resolves through the versioned canonical unit registry
**And** an unregistered conversion defers rather than being approximated

### Story 3.10: Return a Typed Not-Comparable Result When Widening Does Not Apply

As an operator,
I want incompatible parent widening to return an explicit not-comparable result,
So that a widened comparison never silently ranks mixed dimensions.

**Acceptance Criteria:**

**Given** an ancestor whose preferred comparable unit is compatible with its descendant leaves
**When** a widened comparison runs
**Then** one result set is returned across those leaves, expressed in the ancestor's preferred unit

**Given** an ancestor whose preferred unit is incompatible with one or more descendant leaves
**When** a widened comparison runs
**Then** a typed not-comparable result is returned naming the incompatible leaves
**And** no partial ranking mixing dimensions is produced

**Given** an ancestor declaring no preferred comparable unit
**When** a widened comparison is requested
**Then** a typed not-comparable result is returned

**Given** the demonstration required by CAP-3
**When** it is run against one product set
**Then** it shows leaf comparison, facet filtering within that leaf, and parent widening across leaves

### Story 3.11: Override the Comparable Unit for Odd SKUs

As an operator,
I want a rare per-product override when a leaf's preferred unit is nonsense for that SKU,
So that a single outlier does not force the whole leaf to a bad denominator.

**Acceptance Criteria:**

**Given** a product whose leaf preferred unit is inappropriate for it
**When** a `comparable_unit_override` is set
**Then** normalization for that product uses the override
**And** the override records its justification and the actor who set it

**Given** an override is set
**When** the item is inspected
**Then** it is flagged as human-review-worthy

**Given** an override unit that does not resolve in the canonical unit registry
**When** it is submitted
**Then** it is rejected

**Given** a product with no override
**When** normalization runs
**Then** the leaf preferred unit is used, and the override path is not exercised

**Given** the override mechanism
**When** its scope is inspected
**Then** it applies per product and never rewrites the leaf's declared comparable-unit policy

## Epic 4: Staged Agent Pipeline with End-to-End Inspectable Runs

An operator can run discover/create, assign, and extract as three separately-prompted, separately-scored LangGraph stages over an ingest slice, with every run, stage execution, and provider call durably identified, replay-safe, and visible end to end in Phoenix.

Covers FR8, FR9, FR10, FR53, FR54. Governed by AD-2, AD-12, AD-19, AD-21, AD-22, AD-25, AD-34.

### Story 4.1: Identify Every Run, Stage Execution, and Attempt

As an operator,
I want a stable identity for each pipeline run, stage execution, and provider attempt,
So that every number and trace I later read can be joined back to exactly what produced it.

**Acceptance Criteria:**

**Given** an ingest-selection manifest
**When** a pipeline run is launched from it
**Then** the run receives a UUIDv7 `pipeline_run_id` identifying exactly one workflow and supply candidate
**And** one manifest may group several candidate runs

**Given** a running pipeline
**When** a stage begins
**Then** it receives a `stage_execution_id` scoped to the run

**Given** a stage execution
**When** a new provider invocation occurs under it
**Then** it receives a `stage_attempt_id`

**Given** an infrastructure retry of the same work
**When** the run resumes
**Then** the `pipeline_run_id` survives unchanged
**And** a new provider invocation produces a new `stage_attempt_id` rather than reusing the previous one

**Given** vendor identifiers from PgQueuer, LangGraph, and Phoenix
**When** they are stored
**Then** they remain opaque adapter data mapped explicitly to application run and attempt IDs
**And** they are never used as an application primary key

### Story 4.2: Fix the Stage Outcome Envelope in Shared Contracts

As an operator,
I want one versioned stage outcome shape shared by every stage and workflow variant,
So that evaluators read a single contract no matter which candidate produced the result.

**Acceptance Criteria:**

**Given** the `contracts/v1` package
**When** its imports are inspected
**Then** it is framework-free, importing no FastAPI, SQLAlchemy, LangGraph, LangChain, PgQueuer, Phoenix, or OpenTelemetry

**Given** a stage outcome
**When** it is constructed
**Then** its status is exactly one of `success`, `unknown`, `defer`, `invalid`, or `retryable_failure`

**Given** a stage outcome
**When** it is inspected
**Then** it distinguishes a proposal from a committed command receipt
**And** it carries prerequisite and produced revisions plus immutable config identities

**Given** an evaluator
**When** it scores a stage
**Then** the stage outcome is its sole input

**Given** a workflow variant that changes who produces or applies an outcome
**When** its outcome is compared to the baseline
**Then** the schema and commit semantics are identical

**Given** the contracts package
**When** its inventory is checked
**Then** it owns `SourceIdentity`, `CatalogSnapshotRef`, `ProductSnapshot`, `Money`, `EvidenceRef`, typed trait and quantity values, command request and result schemas, and stable domain error codes

### Story 4.3: Store Stage Outcomes Durably and Replay Them

As an operator,
I want a validated stage outcome persisted before it is applied,
So that a retry reapplies the stored result instead of paying for a second model call.

**Acceptance Criteria:**

**Given** a stage execution that has produced a validated outcome
**When** the one-time command application is about to run
**Then** the outcome, request fingerprint, and config versions are already durably stored in application Postgres

**Given** a stored stage outcome
**When** the work is replayed after an infrastructure failure
**Then** the stored outcome is reapplied
**And** no new provider call is issued for that attempt

**Given** a replayed stage
**When** cost and eval figures are recomputed
**Then** they are unchanged by the replay

**Given** Phoenix and provider identifiers attached to a stage execution
**When** replay occurs
**Then** they serve as supplemental provenance only
**And** they are never the sole source used to reconstruct the outcome

**Given** a request whose fingerprint differs from the stored one
**When** replay is attempted
**Then** it is treated as new work rather than silently reusing the stored outcome

### Story 4.4: Emit Telemetry Through a Domain-Owned Port

As an operator,
I want instrumentation expressed as an application port with vendor SDKs confined to adapters,
So that the domain never depends on OpenTelemetry or Phoenix.

**Acceptance Criteria:**

**Given** domain and application packages
**When** their imports are inspected
**Then** they import no OpenTelemetry package and depend only on a thin telemetry port

**Given** the infrastructure layer
**When** it is inspected
**Then** the OTel API and SDK, `opentelemetry-exporter-otlp-proto-http`, OpenInference instrumentors, and Phoenix integration live only there

**Given** an instrumented command or workflow
**When** it emits a span
**Then** the `pricecomp.telemetry.v1` convention supplies `pricecomp.run.id`, `pricecomp.stage.execution_id`, `pricecomp.stage.attempt_id`, `pricecomp.item.id`, `pricecomp.category.id`, immutable prompt, workflow, supply and evaluator versions, `llm.provider`, resolved model, and token usage

**Given** both `gen_ai.*` and OpenInference attributes are present on a span
**When** Phoenix ingests it
**Then** the native OpenInference values win

**Given** a batched provider call covering several items
**When** it is instrumented
**Then** child or linked spans are attached, each carrying its own `pricecomp.item.id`

**Given** a job envelope dispatched to the worker
**When** it is consumed
**Then** W3C trace context propagates from producer to handler

### Story 4.5: Run Discover and Create as Its Own Prompted Stage

As an operator,
I want category discovery and creation to run as a stage with its own prompt and score,
So that its quality can be measured without assignment quality masking it.

**Acceptance Criteria:**

**Given** an ingest slice
**When** the discover and create stage runs
**Then** it uses a prompt dedicated to that stage, referenced by immutable version

**Given** the stage
**When** it needs category context
**Then** it obtains it via the taxonomy search tool
**And** no prompt in this stage contains a full taxonomy or a parent subtree

**Given** the stage produces a category proposal
**When** it is applied
**Then** it invokes the taxonomy create command rather than writing persistence directly

**Given** the stage
**When** its capability is inspected
**Then** it cannot assign a product to a category in the same call that creates one

**Given** the stage completes
**When** its result is read
**Then** it returns a stage outcome scoreable independently of the other two stages

### Story 4.6: Run Assign as Its Own Prompted Stage

As an operator,
I want product assignment to run as a stage with its own prompt and score,
So that assignment accuracy is measurable in isolation against a golden set.

**Acceptance Criteria:**

**Given** a product and a populated taxonomy
**When** the assign stage runs
**Then** it uses a prompt dedicated to assignment, referenced by immutable version

**Given** the assign stage
**When** it gathers candidates
**Then** it uses the taxonomy search tool and considers existing category membership, not only search hits

**Given** the assign stage reaches a decision
**When** it applies the result
**Then** it invokes the product assign command, producing exactly one active leaf membership

**Given** the assign stage cannot choose confidently
**When** it completes
**Then** it returns `defer` or a low-confidence outcome and a deferred item is recorded
**And** it does not force a leaf

**Given** the assign stage
**When** its outcome is scored
**Then** it is scoreable independently of discovery and extraction

### Story 4.7: Run Extract as Its Own Prompted Stage

As an operator,
I want trait extraction to run as a stage with its own prompt and score,
So that extraction failures are visible as extraction failures rather than assignment noise.

**Acceptance Criteria:**

**Given** a product with an active leaf membership
**When** the extract stage runs
**Then** it uses a prompt dedicated to extraction, referenced by immutable version
**And** it applies the trait schema declared for that leaf, referenced by immutable version

**Given** the extract stage
**When** it processes a product
**Then** deterministic extraction runs first and the model is invoked only for residual, low-confidence, or empty values

**Given** the extract stage proposes values
**When** they are applied
**Then** they pass the evidence validator before persistence
**And** uncited non-null values are rejected

**Given** the extract stage returns `unknown` or `defer`
**When** the outcome is handled
**Then** a deferred item is recorded and the run continues

**Given** the extract stage
**When** its outcome is scored
**Then** it is scoreable independently of the other stages

### Story 4.8: Orchestrate the Three Stages in LangGraph

As an operator,
I want the staged pipeline expressed as a LangGraph workflow with Postgres checkpoints,
So that a run survives a crash and resumes rather than restarting.

**Acceptance Criteria:**

**Given** the pipeline
**When** its orchestration is inspected
**Then** LangGraph directly owns stage ordering with no framework-neutral abstraction layer in between

**Given** the checkpointer
**When** it is configured
**Then** `AsyncPostgresSaver` uses `pipeline_run_id` as `thread_id` and a versioned workflow as the checkpoint namespace
**And** strict MessagePack allowlisting is enabled

**Given** graph state
**When** its contents are inspected
**Then** it holds orchestration data only
**And** no business fact is stored solely in graph state

**Given** a graph node performing a business mutation
**When** it executes
**Then** it invokes an application command
**And** it never touches SQL or a repository directly

**Given** a run interrupted by SIGKILL mid-stage
**When** the worker restarts and the work is re-driven
**Then** the run resumes from its last checkpoint rather than re-executing completed stages

### Story 4.9: Launch a Pipeline Run from an Ingest Selection

As an operator,
I want to start a staged run over a chosen ingest slice and watch it reach a terminal state,
So that I can go from selecting products to inspecting results in one operation.

**Acceptance Criteria:**

**Given** an ingest-selection manifest
**When** I launch a pipeline run through the API, MCP, or CLI
**Then** a durable job is enqueued after the launching transaction commits
**And** the worker executes it

**Given** a launched run
**When** its status is queried
**Then** it reports one of `pending`, `running`, `retry_wait`, `completed`, `failed`, or `cancelled`

**Given** a run over a slice containing products that will defer
**When** the run completes
**Then** it reaches a terminal state without human intervention
**And** the deferred items are recorded against that run

**Given** a run that is cancelled
**When** cancellation is requested
**Then** the run reaches `cancelled` and in-flight work stops at the next safe boundary

**Given** the same launch request submitted twice with one idempotency key
**When** both are processed
**Then** exactly one run is created

### Story 4.10: Prove Phoenix Joins Runs Without Double-Counting Cost

As an operator,
I want a contract test showing traces join correctly and token counts are not double counted,
So that the cost and quality numbers I later publish are trustworthy.

**Acceptance Criteria:**

**Given** a completed pipeline run
**When** its trace is opened in Phoenix
**Then** the prompts, tool calls, and resulting writes are visible end to end for that run

**Given** parent spans and leaf LLM spans in one run
**When** token usage is aggregated
**Then** only leaf spans with `span_kind = 'LLM'` are counted
**And** parent-span token propagation does not inflate the total

**Given** the contract test
**When** it runs
**Then** it proves Phoenix can join E1, E2, E3, and E5 views on the run, stage-execution, and item identifiers

**Given** a model in use
**When** cost attribution is checked
**Then** `llm.provider` is present and a matching Settings-to-Models entry resolves
**And** a regex miss that would yield a silent zero cost fails the check rather than passing quietly

**Given** each newly introduced model
**When** its estimated cost is reviewed
**Then** it is reconciled at least once against provider billing

## Epic 5: Deferred — Seeing Where the Agent Fails

An operator can open one read-only web surface listing every deferred item with its stage, reason code, payload snapshot, and Phoenix trace deep link, scan failure patterns by stage and reason without leaving the list, and re-drive any item by CLI.

Covers FR39 and FR40, plus all 21 UX Design Requirements. Governed by AD-8, AD-13, AD-14, AD-24, AD-32, and the `pricecomp Deferred` design and experience spines.

### Story 5.1: Read the Deferred Queue Over the API

As an operator,
I want a read-only query returning deferred items with their stage, reason, payload, and trace reference,
So that a client can render the queue without any write surface existing.

**Gate:** [`GATE-04-review-lifecycle.md`](../../implementation-artifacts/gates/GATE-04-review-lifecycle.md)

**Acceptance Criteria:**

**Given** the read API on the new Python backend
**When** its routes are inspected
**Then** `GET /api/v1/deferred` and `GET /api/v1/deferred/{id}` exist per GATE-04
**And** no POST, PATCH, or DELETE routes exist for deferred items

**Given** deferred items exist
**When** the deferred list query is called
**Then** it returns each item's product reference and name, supermarket and source id, stage, reason code, attempt count, timestamp, trace ID, and Phoenix deep link
**And** results are ordered newest first

**Given** the deferred list query
**When** stage and reason filters are supplied
**Then** they are applied together as a conjunction
**And** omitting a filter returns all values for that dimension

**Given** a deferred item is requested in detail
**When** the query returns
**Then** it includes the immutable payload snapshot and any `evidence_span` context

**Given** the review read surface
**When** its route inventory is inspected
**Then** it exposes no mutating endpoint for deferred items
**And** no reviewer domain write such as leaf reassign, trait edit, or evidence accept exists

**Given** the API
**When** it is deployed
**Then** it remains local or internal, consistent with security being out of scope for this initiative

### Story 5.2: Re-Drive a Deferred Item from the CLI

As an operator,
I want a CLI command that re-drives a deferred item,
So that I can retry a failure through the same handler the pipeline uses, without a write surface in the UI.

**Acceptance Criteria:**

**Given** a deferred item identifier
**When** the re-drive CLI command is run
**Then** it invokes the same application command handler the pipeline uses
**And** it does not reach persistence or SQL directly

**Given** a re-drive is requested
**When** it is dispatched
**Then** a durable job is enqueued after the triggering transaction commits
**And** the handler is idempotent so a duplicate enqueue is a no-op

**Given** a re-drive that defers again
**When** it completes
**Then** the existing deferred row's attempt count increases rather than a duplicate open row being created

**Given** a re-drive that succeeds
**When** it completes
**Then** the deferred item's status reflects resolution
**And** the resulting domain writes are visible through the normal owner tables

**Given** a re-drive of an unknown identifier
**When** it is run
**Then** it fails with a stable domain error code rather than silently doing nothing

### Story 5.3: Establish the Deferred Design Tokens

As an operator,
I want the surface built on the design spine's color, type, and shape tokens,
So that the page reads as deliberate in an interview screenshot rather than as default framework chrome.

**Acceptance Criteria:**

**Given** the stylesheet
**When** color tokens are inspected
**Then** it defines `background #F7F6F3`, `surface #FFFFFF`, `surface-muted #EEF0F2`, `on-surface #1A1D21`, `on-surface-muted #5C6570`, `border #D5DAE0`, `border-strong #9AA3AD`, `primary #1F4B63`, `on-primary #FFFFFF`, `accent #C45C26`, `on-accent #FFFFFF`, `link #1F4B63`, and `focus-ring #1F4B63`

**Given** the reason chip tokens
**When** they are inspected
**Then** `unknown` is `#8A6D1F` on `#F5EED8`, `defer` is `#1F4B63` on `#E4EEF3`, and `low_confidence` is `#6B4F7A` on `#EFE8F3`

**Given** the accent token
**When** its usages are audited
**Then** it appears only on the Phoenix deep link

**Given** the typography tokens
**When** they are inspected
**Then** IBM Plex Sans defines display 28px/600/1.2/-0.02em, title 18px/600/1.3, body 14px/400/1.5, and label 12px/500/1.4/0.04em
**And** IBM Plex Mono defines 12px/400/1.45

**Given** rendered content
**When** type assignment is audited
**Then** monospace carries product IDs, reason codes, stage names, trace IDs, timestamps, and payload JSON
**And** sans carries product titles and chrome

**Given** the shape and spacing tokens
**When** they are inspected
**Then** radii are `sm 2px`, `md 4px`, `lg 6px`, `full 9999px`
**And** spacing defines an 8px unit, 24px gutter, 32px desktop margin, 16px mobile margin, and a 1100px content max

### Story 5.4: Render the Deferred Page Shell

As an operator,
I want a single-purpose page header showing the product name, the view, and how many items are open,
So that I know at a glance what I am looking at and how much is outstanding.

**Gate:** [`GATE-04-review-lifecycle.md`](../../implementation-artifacts/gates/GATE-04-review-lifecycle.md) — route `frontend/app/routes/deferred.tsx`

**Acceptance Criteria:**

**Given** the Deferred route at `frontend/app/routes/deferred.tsx`
**When** it renders
**Then** the page uses the `background` token and the header shows the product name in display type followed by "Deferred"

**Given** open deferred items exist
**When** the header renders
**Then** an open count appears in muted monospace, for example `7 open`

**Given** the header
**When** it renders
**Then** a Refresh control is present

**Given** the application shell
**When** its structure is inspected
**Then** there is no sidebar navigation, no multi-page app shell, and no settings surface

**Given** the page body
**When** it is laid out
**Then** content is a single column constrained to the 1100px content max

### Story 5.5: Render Deferred Rows with Reason Chips

As an operator,
I want each deferred item as a dense flat row carrying its stage and reason,
So that I can scan failure patterns without opening anything.

**Acceptance Criteria:**

**Given** deferred items are loaded
**When** the list renders
**Then** each row shows product name in sans, supermarket and id in mono, stage in mono, a reason chip, attempt count, relative time, and a Phoenix link

**Given** a row
**When** its styling is inspected
**Then** it sits on `surface` with a 1px `border` and `md` radius
**And** no drop shadow or elevation is applied

**Given** a reason chip on a row
**When** it renders
**Then** it is a pill at `full` radius using label typography, colored from its reason token pair
**And** its text is the stored reason code string

**Given** a reason chip on a row
**When** it is clicked
**Then** nothing is filtered, because row chips are display-only

**Given** several deferred items
**When** the list renders
**Then** rows are ordered newest first

**Given** a stage and reason combination
**When** the list is scanned
**Then** both are legible without expanding any row

### Story 5.6: Expand a Row in Place

As an operator,
I want detail to open inside the list rather than in a modal,
So that I keep surrounding context while reading one item's payload.

**Acceptance Criteria:**

**Given** a collapsed row
**When** it is clicked or activated with Enter
**Then** its detail expands directly beneath it
**And** the page does not navigate away

**Given** an expanded row
**When** its detail renders
**Then** it is indented, filled with `surface-muted`, and contains the payload snapshot in monospace, any `evidence_span`, and the Phoenix URL

**Given** an expanded detail region
**When** it is inspected for controls
**Then** it contains no edit control of any kind

**Given** a long payload snapshot
**When** it renders
**Then** it is truncated with a "Show more" control that expands in place
**And** no modal or new page is opened

**Given** an expanding or collapsing row
**When** motion is applied
**Then** it is a transition of roughly 150ms
**And** no celebratory or attention-seeking motion is used

### Story 5.7: Open the Phoenix Trace

As an operator,
I want a deep link from a deferred item into its Phoenix trace,
So that I can confirm the prompt and tool calls and then come back.

**Acceptance Criteria:**

**Given** a deferred item with a trace ID
**When** the row renders
**Then** an "Open trace" control appears in the `accent` color with the `trace_id` in monospace

**Given** the "Open trace" control
**When** it is activated
**Then** the Phoenix trace opens in a new browser tab

**Given** the "Open trace" control sits inside a clickable row
**When** it is activated
**Then** propagation is stopped so the row does not also toggle

**Given** a deferred item with no `trace_id` or no resolvable URL
**When** the row renders
**Then** the control is disabled and shows a muted "No trace"
**And** the row itself remains listed and expandable

**Given** the Phoenix UI
**When** it is reached
**Then** it is not restyled or wrapped in this product's chrome

### Story 5.8: Filter by Stage and Reason with Shareable URLs

As an operator,
I want stage and reason filters reflected in the URL,
So that I can bookmark a filtered view and reopen it during a walkthrough.

**Acceptance Criteria:**

**Given** the filter bar
**When** it renders
**Then** it offers stage and reason chips outlined in `border-strong`
**And** an active chip fills with `primary` on `on-primary`

**Given** the stage filter
**When** a value is chosen
**Then** selection is single-select and the list filters immediately

**Given** both a stage and a reason are selected
**When** the list filters
**Then** the two conditions are combined as a conjunction

**Given** an active filter
**When** it is cleared
**Then** the list returns to all values for that dimension

**Given** filters are applied
**When** the URL is inspected
**Then** it carries `?stage=` and `?reason=` query parameters reflecting the current state

**Given** a URL such as `?stage=assign&reason=low_confidence`
**When** it is loaded directly
**Then** those filters are applied on first render

**Given** the filter bar
**When** its options are inspected
**Then** only stage and reason are offered

### Story 5.9: Handle Loading, Empty, Error, and Stale States

As an operator,
I want honest states for loading, emptiness, and failure,
So that the surface reads truthfully even when there is nothing to show.

**Acceptance Criteria:**

**Given** the list is loading
**When** it renders
**Then** skeleton rows matching the deferred-row anatomy are shown

**Given** no deferred items exist at all
**When** the list renders
**Then** a centered short sentence states "No deferred items." with one line noting ingest may still create them
**And** there is no illustration and no call to action

**Given** filters are applied and match nothing
**When** the list renders
**Then** it states "No items match these filters." and offers a control to clear them
**And** this copy is distinct from the globally empty state

**Given** the list query fails
**When** the error renders
**Then** it shows "Couldn't load deferred items." with a Retry control inline
**And** no modal is used

**Given** the list may be stale
**When** the operator wants fresh data
**Then** the header Refresh control reloads it
**And** no websocket or polling mechanism exists

### Story 5.10: Navigate by Keyboard and Meet the Accessibility Floor

As an operator,
I want keyboard navigation and WCAG 2.2 AA compliance,
So that the surface is usable without a mouse and readable in screenshots.

**Acceptance Criteria:**

**Given** the list has focus
**When** `j` or `k` is pressed
**Then** focus moves between rows

**Given** a focused row
**When** `Enter` is pressed
**Then** the row expands or collapses

**Given** a focused row with a trace
**When** `o` is pressed
**Then** the Phoenix trace opens in a new tab

**Given** all text on the page
**When** contrast is measured against `background` and `surface`
**Then** it meets WCAG 2.2 AA
**And** each of the three reason-chip foreground and background pairs is explicitly verified

**Given** an expand or collapse control
**When** assistive technology inspects it
**Then** `aria-expanded` reflects its state
**And** the detail region is labeled

**Given** stage and reason
**When** they are conveyed
**Then** each is present as text and not by color alone

**Given** a focused interactive element
**When** it renders
**Then** the focus ring uses the `focus-ring` token

**Given** the external Phoenix link
**When** it is announced
**Then** it states that it opens in a new window

### Story 5.11: Adapt the Layout to Narrow Viewports

As an operator,
I want the ledger to stay readable on a narrow screen,
So that a quick check on a phone works even though the surface is designed for desktop.

**Acceptance Criteria:**

**Given** a desktop viewport
**When** the page renders
**Then** it is a single column capped at 1100px with the full row grid visible

**Given** a narrow viewport
**When** the page renders
**Then** filter chips wrap rather than overflowing
**And** row metadata stacks beneath the product name

**Given** any supported viewport
**When** the page renders
**Then** the body does not scroll horizontally

**Given** the product
**When** its platform targets are inspected
**Then** it is web only, with no native mobile application

### Story 5.12: Hold the Read-Only and Visual Restraint Contract

As an operator,
I want the surface to state failures plainly and never imply it can act on them,
So that it stays an honest map of where the agent fails.

**Acceptance Criteria:**

**Given** reason codes are displayed
**When** their text is inspected
**Then** they render exactly as stored — `unknown`, `defer`, `low_confidence`
**And** no euphemism such as "needs a look" is used

**Given** stage names are displayed
**When** their text is inspected
**Then** they match the pipeline's own names such as `assign` and `extract`
**And** no invented UI stage label appears

**Given** all microcopy
**When** it is reviewed
**Then** it contains no emoji status, no exclamatory alerting, and no congratulatory phrasing

**Given** the interaction surface
**When** it is audited
**Then** drag-and-drop, bulk select, inline edit, status transitions from the UI, assignment, and comments are all absent
**And** no control implies a write affordance

**Given** the page
**When** its visual inventory is audited
**Then** it contains no chart, KPI strip, or health-score widget
**And** no drop shadow is used as hierarchy

**Given** the theme
**When** it is inspected
**Then** the surface is light mode only, with no purple or indigo AI gradient and no glow

**Given** all content
**When** its language is inspected
**Then** it is English only

## Epic 6: Eval Harness and the Controlled 2x2 Bakeoff

An operator can score golden assignment accuracy, per-stage quality, and average cost per item against frozen eval manifests, and run two control-flow shapes against two supply shapes on identical data in isolated databases, producing shareable metrics before any winner is declared.

Covers FR41–FR48. Governed by AD-9, AD-19, AD-20, AD-21, AD-25, AD-31.

### Story 6.1: Freeze an Eval Manifest

As an operator,
I want every eval run pinned to an immutable manifest,
So that two results are only ever compared when they were measured the same way.

**Acceptance Criteria:**

**Given** an eval run is prepared
**When** its manifest is created
**Then** it freezes source version, taxonomy version, golden-label version, config versions, and evaluator versions
**And** it receives a UUIDv7 identity

**Given** an eval manifest
**When** it is inspected
**Then** it declares the denominator used for per-item metrics
**And** it declares how failures and defers are treated

**Given** a frozen manifest
**When** any attempt is made to modify it
**Then** the modification is rejected and a new manifest version must be created

**Given** two eval results
**When** they are compared
**Then** the comparison is permitted only when their manifests agree on source, taxonomy, golden labels, denominator, and failure or defer treatment

**Given** a manifest
**When** a run executes against it
**Then** the manifest identity is recorded on the run

### Story 6.2: Make Phoenix the Sole Dataset and Experiment Home

As an operator,
I want datasets, experiments, and traces to live only in self-hosted Phoenix,
So that there is one place to inspect a run and no second trace store to reconcile.

**Acceptance Criteria:**

**Given** the observability stack
**When** its components are enumerated
**Then** self-hosted Phoenix 19.11.1 under ELv2 is the only trace store, dataset home, experiment home, and run UI

**Given** the codebase
**When** it is searched for a custom agent-run trace UI
**Then** none exists, because Phoenix's run UI covers inspectability

**Given** the deployment
**When** it is inspected
**Then** Arize AX and any paid observability tier are absent
**And** Phoenix is not exposed as a third-party managed feature

**Given** versioned datasets and experiments
**When** raw trace retention expires at 30 days
**Then** the datasets and experiments persist independently

**Given** an eval dataset
**When** it is versioned
**Then** earlier versions remain retrievable for re-running a prior experiment

### Story 6.3: Score Golden Assignment Accuracy

As an operator,
I want assignment measured against a labeled golden set,
So that I can state how often the agent puts a product in the right leaf.

**Acceptance Criteria:**

**Given** a golden set of products with known correct leaves
**When** it is created
**Then** it is stored as a versioned Phoenix dataset referenced by immutable identity

**Given** an assign stage run over the golden set
**When** the E1 evaluator executes
**Then** it reports assignment accuracy against the labeled leaves

**Given** an item that deferred rather than being assigned
**When** accuracy is computed
**Then** it is counted according to the manifest's declared defer treatment rather than silently dropped

**Given** a corrected item from Phoenix annotations
**When** it is promoted
**Then** it can be added to the golden set as a new dataset version

**Given** an E1 result
**When** it is recorded
**Then** it carries its manifest identity, prompt version, model, and provider

### Story 6.4: Score Each Stage Independently

As an operator,
I want a separate quality score per stage,
So that I can tell whether a bad run came from discovery, assignment, or extraction.

**Acceptance Criteria:**

**Given** the three pipeline stages
**When** the E2 evaluators run
**Then** each stage has its own eval slice and its own score

**Given** a stage outcome
**When** an evaluator scores it
**Then** the stage outcome envelope is the evaluator's sole input

**Given** a run where one stage performs poorly
**When** the per-stage scores are read
**Then** the weak stage is identifiable without inspecting the others

**Given** the stage evaluators
**When** they execute
**Then** they run as paired Phoenix dataset experiments alongside cost and speed

**Given** an evaluator
**When** it is referenced
**Then** it resolves by immutable version recorded on the result

### Story 6.5: Compute Average Cost per Item per Stage

As an operator,
I want cost expressed as total stage cost divided by items processed,
So that I can compare candidates on spend without building per-product attribution.

**Acceptance Criteria:**

**Given** a completed stage over a selection
**When** E3 is computed
**Then** it reports total stage cost divided by all selected items, including those that deferred or failed

**Given** spans for a run
**When** cost is aggregated
**Then** only leaf spans with `span_kind = 'LLM'` are summed
**And** parent-span token propagation does not double count

**Given** the E3 metric
**When** its scope is inspected
**Then** exact per-product cost attribution and arbitrary cost group-by are absent, as they are explicitly not requirements

**Given** a model whose price pattern does not match a Settings-to-Models entry
**When** cost is computed
**Then** the setup check fails loudly rather than reporting a silent zero

**Given** an E3 figure for a newly introduced model
**When** it is published
**Then** it has been reconciled at least once against provider billing

### Story 6.6: Compare Models and Context Configurations

As an operator,
I want an E5 experiment comparing models and context configurations,
So that model choice is evidence-led rather than assumed.

**Acceptance Criteria:**

**Given** the two provider adapters
**When** an E5 experiment is configured
**Then** it compares model and context configurations across them on the same eval set and ingest slice

**Given** an E5 run
**When** its configuration is recorded
**Then** provider, resolved model, structured-output method, schema and strictness, sampling, output limit, timeout, retry policy, streaming mode, and provider options are all captured immutably

**Given** E5 results
**When** they are read
**Then** quality, cost, and speed are reported per configuration

**Given** a model family that neither adapter covers
**When** E5 requires it
**Then** adding a third provider adapter becomes justified under its named revisit condition

**Given** an E5 experiment
**When** it is re-run from its manifest
**Then** it reproduces its configuration exactly

### Story 6.7: Isolate Each Bakeoff Candidate in Its Own Database

As an operator,
I want every candidate to run against a clone of one frozen baseline,
So that no candidate can see another's writes and the experiment measures design rather than interference.

**Acceptance Criteria:**

**Given** an immutable Postgres baseline containing frozen catalog observations, taxonomy and config versions, and a checksum identity
**When** a candidate run starts
**Then** a disposable database is cloned from that baseline for it

**Given** several candidates running
**When** their databases are inspected
**Then** no live mutable owner database is shared between them

**Given** the isolation requirement
**When** the test suite runs
**Then** a test proves no candidate can observe another candidate's writes

**Given** a completed candidate run
**When** cleanup executes
**Then** the candidate database is deleted

**Given** candidate runs holding separate databases
**When** they execute concurrently
**Then** the single-writer advisory lock does not block them, because it is scoped per application database

### Story 6.8: Run the Two-by-Two Control-Flow and Supply Bakeoff

As an operator,
I want the four candidate combinations run on one harness,
So that I have comparable numbers for two control-flow shapes and two supply shapes.

**Acceptance Criteria:**

**Given** the MVP arms
**When** they are enumerated
**Then** control flow is O4 explicit graph and O5 graph of stages with tools inside a stage
**And** supply is P2 one product at a time and P4 agent search on demand

**Given** the four combinations
**When** they run
**Then** each executes inside LangGraph against identical datasets, ingest slices, commands, controlled models and prompts, instrumentation, eval definitions, and durability

**Given** a candidate workflow or supply shape
**When** it is implemented
**Then** it is a separate graph or configuration
**And** business mutation still goes through the same application commands

**Given** the bakeoff arms
**When** they are checked against the negative contract
**Then** no arm implements or lays groundwork for a kill-piled option, including P1, P5, P6, P7, P8, and O6
**And** no embedding-dependent arm such as P3, P9, or P10 is present

**Given** all four combinations complete
**When** their results are collected
**Then** each carries golden assignment accuracy, per-stage scores, average cost per item, speed, and inspectability evidence

### Story 6.9: Publish Shareable Results Without Declaring a Winner

As an operator,
I want the bakeoff to produce a shareable comparison that stops short of picking a winner,
So that the decision waits for evidence and the artifact stands on its own as a portfolio piece.

**Acceptance Criteria:**

**Given** the four candidate results
**When** the comparison is produced
**Then** it presents quality, cost, speed, and inspectability side by side with their manifest identities

**Given** the comparison artifact
**When** it is reviewed
**Then** no control-flow or supply winner is declared

**Given** any document or code comment
**When** it is checked before the full metric set exists
**Then** no option is stated as preferred in writing

**Given** the complete metric set exists
**When** a selection is eventually made
**Then** it cites the specific figures that justify it

**Given** the success signal for the initiative
**When** it is evaluated
**Then** a filtered ingest slice has yielded comparison-ready rows, re-import has not wiped LLM attributes, runs are inspectable end to end in Phoenix, and the 2x2 numbers are shareable
