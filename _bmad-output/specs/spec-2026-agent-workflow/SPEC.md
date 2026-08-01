---
id: SPEC-2026-agent-workflow
companions:
  - glossary.md
  - architecture-diagrams.md
  - explore-bakeoffs.md
  - kill-pile.md
  - ../../brainstorming/brainstorm-2026-agent-workflow-2026-07-30/morphological-matrix.md
sources:
  - ../../../docs/specs/2026-scope.md
  - ../../brainstorming/brainstorm-2026-agent-workflow-2026-07-30/brainstorm-tasks.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# 2026 Agent Workflow

## Why

**Pain + opportunity.** The current TypeScript split (data-importer + backend) burns tokens dumping full taxonomies, conflates discover/assign/extract in one hard-to-eval LLM call, wipes LLM attributes on re-import (D6), and lacks a golden eval set — so accuracy, cost, and agent quality cannot be measured or showcased. The near-term product is a **structured, comparison-ready product DB** (not shopper-facing features): substitutability category + traits + shelf price + normalized comparable price. This initiative rebuilds ingest and agent flow as a Python monolith so operators can run bulk/single/filtered ingest through one staged pipeline, keep taxonomy coherent under automation-first non-blocking HITL, and bake off orchestration and product-supply strategies with shareable metrics.

**Scope posture (2026-08-01).** MVP is deliberately reduced to the shortest path that still yields inspectable agent runs and shareable performance graphs. Production-grade concurrency, cutover, and integrity machinery that buys no showcase evidence is deferred, not designed away — see Non-goals and `explore-bakeoffs.md`.

## Capabilities

- **CAP-1**
  - **intent:** Operator can ingest products as a bulk catalog, single upsert, or filtered subset (source category / keyword) through the same pipeline.
  - **success:** One ingest-selection primitive serves all three — bulk is the empty filter, single is a filter of one; no mode-specific agent path exists.
- **CAP-2**
  - **intent:** System runs staged discover/create → assign → extract with separate prompts and eval slices.
  - **success:** Each stage can be scored independently (E2); same-call create+assign is impossible by design.
- **CAP-3**
  - **intent:** System maintains a substitutability taxonomy where each product belongs to exactly one leaf, leaves are consumer-fine for default compare, facets filter within a leaf, and parents widen compare scope.
  - **success:** Taxonomy is a tree (not a graph); product↔leaf is many-to-one; a demo shows leaf compare, facet filter, and parent widen on the same products.
- **CAP-4**
  - **intent:** System extracts structured traits such that every non-null value cites a verbatim `evidence_span`, and unknown/defer routes to review rather than inventing values.
  - **success:** Deterministic validator rejects uncited non-null traits; unknown/defer items land in DLQ (H2).
- **CAP-5**
  - **intent:** System produces comparable unit quantities and normalized prices using category `preferred_comparable_unit` (required on compare leaves), without silently fabricating conversions.
  - **success:** Basket math deterministically picks the accepted quantity matching the preferred unit (or parent when widening); missing/unconvertible yields null + defer/DLQ. Normalized price is derived on read from the current shelf-price and quantity revisions — never from a cache stored on a quantity row.
- **CAP-6**
  - **intent:** Agents obtain category context by searching the taxonomy on demand rather than receiving a full (or parent-subtree) dump.
  - **success:** No prompt path dumps the full taxonomy or parent subtree; agent search (C2) is the category-context path.
- **CAP-7**
  - **intent:** Re-import and upsert merge LLM-extracted attributes with deterministic fields and never wipe prior LLM values.
  - **success:** Re-running import on a product that already has LLM traits preserves those traits unless explicitly overwritten by a validated merge; regression test covers the D6 wipe bug.
- **CAP-8**
  - **intent:** System prefers matching an existing category before creating, creates for real when no good match (no drafts), and runs post-bulk hygiene that can merge, rename, edit, reparent, reassign, flag for HITL, and fix leaf coherence.
  - **success:** One post-bulk hygiene run over the categories touched by that run demonstrates at least merge/reassign/coherence fix; no provisional/draft category state in MVP; agents consider existing membership, not only search hits.
- **CAP-9**
  - **intent:** Humans can see where the agent failed or deferred, asynchronously and without blocking the pipeline, and can re-drive those items.
  - **success:** Pipeline completes without waiting on a human; low-confidence, unknown, and defer outcomes land in `deferred_items` and appear on a first-party read-only dashboard with stage, reason code, payload snapshot, and Phoenix trace deep link; an operator can re-drive an item by CLI command.
- **CAP-10**
  - **intent:** Operator can compare control-flow and product-supply strategies on a shared eval harness with golden assign accuracy, per-stage scores, average cost per item, and model/context bakeoff metrics.
  - **success:** Same eval set + ingest slice runs for two control-flow workflow shapes (O4/O5) and two product-supply shapes (P2 and P4) inside LangGraph; shareable metrics exist before a workflow or supply shape is selected. Capability surface and framework vendor are not bakeoff-gated (see Constraints).

## Constraints

- Python monolith + DDD; one backend owns agent flow, REST, and data import; Devcontainers for the environment.
- Security is out of scope for this initiative.
- Catalog design must admit non–Swiss-grocery sources with minimal adaptation.
- Durable source identity is `(source_namespace, source_product_id, optional source_variant_id)`; product name and URLs are mutable observations, never identity. A source adapter without a trustworthy stable ID must explicitly defer/fail rather than fall back to presentation fields.
- Substitutability definition is prose rubric + few-shot labeled pairs (S1+S2); comparison primitive is consumer substitutability, not retailer taxonomy.
- Import/source categories filter ingest only; they are not comparison primitives (see `glossary.md`).
- Unit/trait extract is deterministic-first (sources: `unit` → `price_text` → name); high-confidence deterministic success skips LLM; LLM extract only for residuals/low-conf/empty with `evidence_span` (T1). T2 is not MVP default.
- **Evidence shape:** an `evidence_span` names the source field, the verbatim substring, and a SHA-256 hash of that field's text at extraction time. Byte-offset addressing, Unicode normalization guarantees, and revision carry-forward/invalidation cascades are out of MVP.
- Category has `preferred_comparable_unit` + optional `secondary_comparable_units[]`; product stores revisioned `shelf_price` + `quantities[]` (kind `net_content|item_count|price_basis`, qty, unit, source deterministic|inferred, evidence). **Normalized price is derived on read** from the current shelf-price and quantity revisions; results always carry currency and comparable unit. No normalized-price cache lives on quantity rows, and no indexed comparison projection is built in MVP. Rare `comparable_unit_override` is HITL-worthy only.
- **Single-writer runtime.** MVP assumes one operator and one worker executing pipeline work. Taxonomy topology compare-and-set, review-request generation watermarks, worker leases and fencing tokens, and a transaction-joining queue producer are out of scope; job enqueue happens after commit and handlers are idempotent so replay is safe. The premise is enforced mechanically — a worker takes a Postgres advisory lock at startup and a second worker exits rather than starting — because the failure mode of accidental concurrency is silent taxonomy corruption and poisoned eval baselines, not a visible crash.
- **Capability surface (O1 first):** in-product agent tools (`category search`, `category create`, `product assign`, `traits extract`) are exposed as MCP / tool calls. Implement them as one command layer with the MCP surface as a **thin** adapter over it, so an AXI-style CLI (O2) or Code Mode (O3) adapter can be added when a concrete limit is hit — token blowup on tool definitions, or intermediate data that should never enter context. Surface choice is deferred, not killed; O2/O3 stay in `explore-bakeoffs.md` as later arms.
- **Framework vs workflow:** LangGraph is the selected MVP orchestration framework. Control-flow workflow shapes (O4/O5) and product supply (P2, P4) stay in the explore set — do not select a winner until bakeoff metrics exist (`explore-bakeoffs.md`). Implement candidates inside the same framework with shared commands, persistence, instrumentation, evals, and durability so the experiment measures workflow design rather than vendor differences.
- **Observability + eval platform: Arize Phoenix, self-hosted** — one container (ELv2, not OSI open source), pointed at a dedicated database inside the existing Postgres 18 instance via `PHOENIX_SQL_DATABASE_URL`. It is the single trace store, dataset/experiment home, and run UI. Set per-project retention from day one; trace payloads carry verbatim catalogue text and `evidence_span` values.
- **Instrumentation:** domain/application code owns a telemetry port and imports no OpenTelemetry package; `opentelemetry-api`, SDK, exporter, auto-instrumentors, and span-kind attributes live in infrastructure adapters. Phoenix ≥ 15.10.0 converts `gen_ai.*` to OpenInference at ingest (including `gen_ai.usage.*` → `llm.token_count.*`), so a native OTel emitter needs no attribute-mapping adapter; OpenInference attributes still win where both are present. Cost additionally requires `llm.provider` plus a matching Settings → Models entry — a regex miss yields a silent $0, so cost visibility is a setup check, not an assumption.
- **E3 granularity:** average cost per item per stage (total stage cost ÷ items processed) is sufficient. Exact per-product cost attribution and arbitrary cost group-by are **not** requirements. Aggregate leaf `span_kind = 'LLM'` spans only — parent-span token propagation double-counts. Reconcile Phoenix's price-table estimate against provider billing at least once per model introduced by E5.
- **Two LLM providers.** The LLM port ships adapters for exactly two providers in MVP; E5 model/context bakeoff needs no more.
- **H1 is first-party and read-only in MVP, deliberately.** It exists to show *where the agent fails*, not to be a review console: list and inspect deferred items, follow the Phoenix trace, re-drive by CLI. Domain write actions (leaf reassign, trait edit, evidence accept/reject) are deferred. Phoenix annotations remain available for span-level labels and for promoting corrected items into the golden set; Phoenix labeling queues are Arize AX–only and are not adopted.
- **H2 DLQ is a first-party Postgres table** (`deferred_items`: product ref, stage, reason code, attempt count, payload snapshot, `trace_id`, status) with a repository and a re-drive command. The Phoenix trace deep link is stored on the row; H1 reads from this table.
- **Cutover is a fresh rebuild.** New databases are provisioned and one immutable source manifest is replayed through the Python importer without legacy AI-derived state; legacy stays read-only and the frontend stays on the legacy API during the rebuild. No freeze/restore drill, reconciliation gate ceremony, observation window, or routing-rollback rehearsal is required — recovery is re-import.
- Kill-pile options must not be built toward (`kill-pile.md`).
- Formal specs for this work live under `_bmad-output/specs/`, not `.kiro`.

## Non-goals

- Shopper-facing features (receipt upload, basket optimizer, nutrition Q&A, etc.) in this initiative.
- Security hardening / threat modeling for this initiative.
- Pre-selecting a control-flow workflow shape (O4/O5) or product-supply shape before eval bakeoff. (Capability surface and orchestration framework are intentionally pre-picked — see Constraints.)
- A custom agent-run trace UI (E4) — Phoenix's run UI covers inspectability; building one is redundant.
- Arize AX, or any paid observability tier, in this initiative.
- Provisional/draft categories (N2); graph / lateral “also-comparable” edges (deferred unless tree+facets fail).
- **Embeddings in MVP** — no pgvector store, no revisioned product embeddings, no embedding-similarity ingest filter, and no embedding-dependent supply arms (P3/P9/P10) or C4 category shortlist.
- **An indexed comparison-price projection** — normalized price is derived on read; fail-closed serveability, revision-linked rows, and atomic generation switches are deferred until read performance is measured to be a problem.
- **Catalog snapshot completeness semantics** — completeness attestation, absence-driven deactivation, and replay-ordering equality checks are out; ingest replaces imported facts for the products it observes and touches nothing else.
- **Concurrency-safety machinery** — see the single-writer constraint.
- **Reviewer domain writes in MVP** — see the H1 constraint.
- **Periodic scheduled hygiene** — hygiene runs post-bulk over the run's touched categories only.
- **REST↔MCP equivalence contract-test suite** — both adapters call the same commands; one mount/list/call smoke test is enough.
- Everything listed in `kill-pile.md` (full taxonomy dumps, blocking HITL, same-call assign+create, T3 force-unit, etc.).

## Success signal

A filtered ingest slice yields comparison-ready rows (leaf category + cited traits + shelf + normalized comparable price where convertible); re-import does not wipe LLM attributes; every run is inspectable end to end in Phoenix (prompts, tool calls, writes); golden assign + per-stage + average-cost-per-item metrics exist; two control-flow shapes and two supply shapes (P2, P4) have been run on the same harness with shareable numbers — with no winner declared until then.

## Assumptions

- Formal-spec home is `_bmad-output/specs/` (this folder); `.kiro` is legacy for new agent-workflow work.
- Morphological matrix stays an adopted companion so morph IDs remain the shared vocabulary for bakeoffs without inlining the full matrix into the kernel.
- Runtime faithfulness beyond “evidence_span ⊆ source text” is eval-owned for MVP (no extra confidence score / second-pass verifier required).
- MVP runs as a single operator against a single worker; the single-writer constraint is a scope choice, not a claim that the design cannot be hardened later.

## Resolved questions

- **Inspectability at MVP (resolved 2026-07-31):** self-hosted Phoenix provides the run/trace UI, versioned datasets and experiments; no custom agent-run UI (E4) is built. Selection rationale and the rejected alternatives (Logfire + Opik pairing, Langfuse, Opik alone) are in `../../planning-artifacts/research/technical-vendor-selection-eval-orchestration-observability-research-2026-07-31.md`.
- **Vendor shape (resolved 2026-07-31):** single self-hosted platform rather than a best-of-breed pairing. Two relaxations made it viable — average cost per item is enough (no need for Logfire's arbitrary SQL over spans) and the reviewer queue is wanted in-house anyway (no need for Opik's annotation queues).
- **Framework selection (resolved 2026-07-31):** LangGraph is selected on workflow expressiveness, Postgres checkpoints, maturity, and Phoenix integration. CAP-10 compares workflow shapes implemented inside LangGraph; it does not compare orchestration vendors.
- **Category coherence timing (resolved 2026-07-31, narrowed 2026-08-01):** assignment performs immediate structural and per-product semantic checks; category-wide coherence runs after bulk ingest over the categories that run touched, not on a schedule.
- **Reconciliation dirty set (resolved 2026-07-31, simplified 2026-08-01):** category-affecting mutations record the affected category on a coalesced review-request row. Under the single-writer constraint no generation watermark or fencing token is required; concise trigger facts and Phoenix run/trace references provide context without a domain-event journal.
- **MVP scope reduction (resolved 2026-08-01):** eleven cuts accepted to shorten time-to-first-graph — no embeddings (supply arms become P2 vs P4), fresh-rebuild cutover, no snapshot completeness semantics, derive-on-read normalized price, single-writer runtime, read-only review dashboard, two LLM providers, thin MCP adapter without an equivalence suite, post-bulk-only hygiene, simplified evidence shape, and one ingest-selection primitive. The showcase spine — staged prompts with separate eval slices, search-backed category context, tree/facet/parent demo, cited traits with defer→DLQ, merge-never-wipe, Phoenix E1/E2/E3/E5, and a 2×2 bakeoff — was held intact.
