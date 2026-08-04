# 2026 Scope

## High-level long-term goals of the repo

- LLM observability
  - Human feedback collection
  - LLM fine-tuning (later)
- Multi-step workflows
- Revised workflow for agentic capabilities
- Ability to ingest:
  - Large batches of products for bulk import / bulk update
  - Single element for ingest / update
  - Specific subsets of the dataset (by imported category, by keyword; by embedding similarity once embeddings return — deferred from MVP)
- Python backend
- Domain Driven Design
- Revised data model
- Cache efficiency — don't repeat requests (middleware that caches every request?) and avoid dev cost spikes

## Product (near-term)

- **Near-term goal:** a structured product DB (categories + traits) — not shopper-facing features yet.
- **Comparison-ready row** = substitutability category + traits + shelf price + normalized comparable price.
- **Terminology:** _import/source category_ = filter only; _substitutability category_ = comparison primitive (consumer substitutability, not retailer taxonomy).

## Current workflow

1. Data import
   1. Parse CSV, lightweight trait detection by name parsing and unit parsing.
2. Category discovery — group products by consumer substitutability
   1. Select set of products by categories
   2. LLM generates array of _new_ categories based on prompt rules and existing categories
   3. Insert DB categories
   4. Log agent execution
3. Schema generation — define per-category attribute schemas
4. Attribute extraction — fill structured traits on each product

## Current issues

- Token efficiency: 1 large LLM call vs many small LLM calls? (also ties into caching, as large calls have more variance) 
- Token efficiency: Entire category taxonomy dumped into model context
- Accurary and error rate? Large prompt does 1 LLM call to handle (1) check against existing categories (2) category creation and (3) product assignment. Harder to evaluate (designing an eval, measuring token usage per item, ...) and compare performance (e.g. across models).
- How to handle updates of a single modified source record?
- Traits and units extraction is split across the codebase (partially done deterministically at import time, useful for debug , but potentially not saving any tokens as verified by LLM anyway)
- Observability: custom built, not easily reviewable at scale, not fed back into the agent. 
- No eval set
- Potentially missing self-correcting behavior? (e.g. deleting and merging categories) 
- TypeScript is quite verbose for this workload compared to Python.
- data-importer and backend are split - unifying could increase reuse and correctness.
- Unit extraction fails often.
- No possibilty for the LLM to flag/defer a decision for human review
- Unclear policy regarding which traits go in which category
- "category" ambiguous term. Should be clarified that import category are used exclusively to filter imports (useful in development)
- **Hard requirement (D6):** Bug: Importer writes attributes with deterministic flags (bio, fairtrade, …) and on upsert replaces the whole column, so re-imports will wipe LLM extracted attributes — must merge, never wipe
- Core specs are stored in .kiro instead of standardized cross-agent and human-surfaced folder.

## New workflow

> **MVP scope reduction (2026-08-01).** Eleven items below were cut from MVP to shorten time-to-first-graph. **None are killed** — each is deferred with a named revisit condition in "Deferred from MVP" below. What's actually rejected (not just deferred) lives in [architecture.md § Won't build](architecture.md#wont-build). Technical invariants live in [architecture.md](architecture.md); the read-only review page's UX spec is [deferred-page.md](deferred-page.md); the current build plan is [../plans/roadmap.md](../plans/roadmap.md).

**Stack:** Python monolith + DDD; one backend for agent flow, REST, and data import. Devcontainers setup.

**Pipeline (same for all ingest modes):** bulk / single upsert / filtered subset → staged prompts (discover/create → assign → extract) → category context via agent search (C2) → explore orchestration (O) and product supply (P) under eval → validators → merge upsert → hygiene → non-blocking HITL.

### Commitments

- **Ingest:** one filter — bulk is the empty filter, single is a filter of one, filtered subset is the general case. **Same pipeline** for all three, so no separate three-mode equivalence acceptance is needed
- **Stages (I9):** separate prompts / eval slices for discover/create, assign, extract
- **Category context (C2):** agent search (MCP/CLI-like); no full taxonomy dump. C4 embed shortlist deferred with embeddings
- **Substitutability (S1+S2):** prose rubric + few-shot pairs; comparison primitive = consumer substitutability
- **Traits (I3):** mandatory `evidence_span` on non-null traits; allow `unknown` / `defer` → DLQ (H2). An `evidence_span` is source field + verbatim substring + SHA-256 hash of that field's text (byte offsets / NFC addressing deferred). Runtime faithfulness beyond span-in-source left to eval for now (no extra confidence/second-pass MVP requirement).
- **Persist (D6):** upsert **merges** LLM attributes — never wipe on re-import. Dedicated regression test is mandatory
- **Create/merge:** prefer match-existing before create (I7); eager create only when no good match (N1); post-bulk hygiene over the categories that run touched (M5). **No provisional/draft categories (N2)** in MVP — create for real or not at all; anti-fragmentation via I7 + hygiene. Periodic scheduled hygiene (M2) deferred
- **Hygiene ops (M5):** the operation set is unchanged by the reduction — not merge/delete only, but also rename, edit, reparent/move (incl. create parent), reassign products, and flag products for re-triage / HITL. Includes **category coherence**: review a leaf’s member products and fix bad assigns / splits / merges — not only cross-category duplicate detection. Only the *scheduling* narrowed: post-bulk over touched categories, not periodic.
- **Taxonomy shape:** product ↔ substitutability category is **many-to-one at the leaf** (not many-to-many). Categories form a **tree** for MVP (not a graph). Graph / lateral “also-comparable” edges deferred unless tree+facets cannot express recurring cross-branch cases.
- **Granularity (G2+G5+G6):** consumer-fine **leaves** for default compare; **facets** for within-leaf filters (organic, fat%, …); **parents** for widen-scope compare (e.g. fresh vs UHT via parent `cow milk`). Rule of thumb: separate leaf if shoppers would not silently swap; facet if same class / preference filter; parent if useful only to widen.
- **Units (T4+T5):** category has `preferred_comparable_unit` (required on compare leaves) + optional `secondary_comparable_units[]`. Product stores `shelf_price` + `quantities[]` (each: qty, unit, source labeled|inferred, evidence_span). **Normalized price is derived on read** from the current shelf-price and quantity revisions — no cache on the quantity row, and no indexed comparison projection in MVP. Results always carry currency and comparable unit. Default basket math picks the row matching preferred (leaf, or parent when widening). Missing/unconvertible → null + defer/DLQ — no silent fake normalize. Rare `comparable_unit_override` only when preferred is nonsense for that SKU (HITL-worthy). T3 (force all into category unit) killed.
- **Unit/trait extract (T1):** deterministic first (extend sources: `unit` → `price_text` → name); **on high-conf success skip LLM** (no always-verify — that would not beat T2 on tokens). LLM extract stage only for residuals / low-conf / empty, with `evidence_span`; unknown → DLQ. Fixable parser gaps (bare unit words, alt count vocab, Denner `(qty unit)` in price_text) are deterministic work. T2 (LLM-only) not MVP default.
- **Human loop:** non-blocking only — async low-confidence dashboard (H1) + unknown→DLQ (H2)
- **Eval / observability MVP:** golden assign set (E1), per-stage evals (E2), average cost per item (E3), model/context bakeoff (E5) — on **self-hosted Arize Phoenix** (single platform; no custom run UI)
- **Human loop surfaces:** H1 and H2 are first-party, not vendor label queues. H1 is **read-only in MVP** — list, filter, inspect payload, open Phoenix trace; re-drive is a CLI command. Its job is to show *where* the agent fails; reviewer domain writes deferred
- **Capability surface:** start at MCP / tool calls (O1) as a **thin** adapter over one command layer; O2/O3 only if a concrete limit appears
- **Runtime:** single operator, no job queue. Ingest/pipeline/hygiene runs are triggered directly (CLI today) and run to completion; taxonomy-mutating commands take a Postgres advisory lock for their duration so an overlapping run fails loudly instead of corrupting topology. LangGraph node-level `RetryPolicy` (plus the LangChain provider clients' own retry/backoff) covers transient LLM failures — no durable dispatch layer needed for that
- **Cutover:** fresh rebuild — provision new databases and replay one immutable source manifest; legacy (including the React UI) stays read-only on the NestJS API. Recovery is re-import
- **Providers:** two LLM provider adapters; E5 needs no more
- **Portfolio showcase:** inspectable agent runs in Phoenix + shareable bakeoff metrics (2 control-flow × 2 supply under the same harness)

### Explore under eval (not fixed yet)

- **Control flow (O4/O5):** LangGraph/state-machine, hybrid — bake off; do not pre-pick
- **Product supply (P2/P4):** one-at-a-time vs agent search — bake off. Gives a 2×2 with control flow and needs no vector store
- **Capability surface (O2/O3):** deferred arms only; O1 adopted first

## Deferred from MVP (deferred, **not** killed)

Cut on 2026-08-01 to shorten time-to-first-graph. Each has a revisit condition; none may be treated as a rejected option. The rejected options are in `kill-pile.md` and that list did not change.

| Deferred | Revisit when |
| --- | --- |
| Embeddings / pgvector; embedding-similarity ingest filter; P3/P9/P10 supply arms; C4 shortlist | C2 agent search shows a measured context-recall or cost ceiling on the eval harness |
| Indexed comparison-price projection (revision-linked, fail-closed, generation switch) | Derive-on-read comparison queries are measured too slow at the target catalog size |
| Snapshot completeness attestation, absence-driven deactivation, replay-ordering equality | A second source adapter, or a source that genuinely delists products, is onboarded |
| Concurrency machinery: taxonomy topology CAS, generation watermarks, leases/fencing, transaction-joining queue producer | More than one worker or writer runs concurrently — the advisory lock makes this a deliberate choice |
| Durable job queue (PgQueuer) for dispatch, retry, and a separate `worker` role | Scheduled/unattended triggering is wanted (cron ingest, automatic hygiene) or more than one trigger source runs concurrently — MVP triggers everything by direct, synchronous command invocation |
| Reviewer domain writes in H1 (leaf reassign, trait edit, evidence accept/reject) | The read-only queue proves worth acting on in-app rather than by CLI |
| Periodic scheduled hygiene (M2) | Post-bulk hygiene is shown to miss drift between runs |
| Gated cutover ceremony: freeze/restore drill, reconciliation gates, observation window, routing rollback | The system holds data that cannot be recovered by re-import |
| Byte-offset / NFC evidence addressing; enrichment carry-forward invalidation | Evidence disputes or multi-revision source drift actually appear |
| Third LLM provider adapter | E5 needs a model family the two adapters do not cover |
| REST↔MCP equivalence contract suite | The two adapters stop being thin wrappers over one command layer |
| Crash-window / multi-writer test suites | They return with the concurrency machinery above |

Note the coupling: reinstating **reviewer domain writes** or **periodic hygiene** reintroduces a second concurrent writer, which reopens the concurrency machinery row. Bakeoff parallelism does *not* — each candidate holds its own database.

## Open questions

_None currently open — the two that stood here (category coherence timing, reconciliation dirty set) were resolved below._

## Resolved questions

- **Inspectability at MVP (resolved 2026-07-31):** self-hosted Arize Phoenix is the run/trace UI, dataset/experiment home, and eval harness. No custom agent-run UI (E4). Chosen for essential coverage + popularity + simplest self-host path (one container on existing Postgres). Canonical write-up: `_bmad-output/planning-artifacts/research/technical-vendor-selection-eval-orchestration-observability-research-2026-07-31.md`; contract: `_bmad-output/specs/spec-2026-agent-workflow/SPEC.md`.
- **Framework selection (resolved 2026-07-31):** LangGraph is the MVP orchestration framework. The bakeoff compares workflow shapes implemented inside it, not orchestration vendors.
- **Category coherence timing (resolved 2026-07-31, narrowed 2026-08-01):** assignment does immediate structural and per-product semantic checks; category-wide coherence runs after bulk ingest over the categories that run touched. Not per-assign, and not on a schedule.
- **Reconciliation dirty set (resolved 2026-07-31, simplified 2026-08-01):** category-affecting mutations upsert one coalesced review-request row per affected category, carrying concise trigger facts and Phoenix references — no full-DB scan and no domain-event journal. Under the single-writer runtime this needs no generation watermark or fencing token.
- **MVP scope reduction (resolved 2026-08-01):** eleven cuts accepted to shorten time-to-first-graph — see "Deferred from MVP" above. The showcase spine was held intact: staged prompts with separate eval slices, search-backed category context, tree/facet/parent demo, cited traits with defer→DLQ, merge-never-wipe, Phoenix E1/E2/E3/E5, and a 2×2 bakeoff.

## Glossary

- **Import / source category** — retailer or CSV taxonomy label, used only to filter ingest subsets. Not a comparison primitive.
- **Substitutability category** — our taxonomy node for consumer substitutability (products a shopper would treat as interchangeable). The comparison primitive.
- **Leaf** — finest substitutability category, used for default cross-retailer price compare. Product ↔ leaf is many-to-one.
- **Facet** — within-leaf preference filter (organic, fat%, brand tier...). Doesn't create a new leaf.
- **Parent** — coarser tree ancestor used to widen compare scope (e.g. fresh vs UHT via parent "cow milk").
- **Comparison-ready row** — a product with substitutability leaf + structured traits + shelf price + normalized comparable price (when convertible).
- **Source identity** — stable `(source_namespace, source_product_id, optional source_variant_id)` from a versioned adapter. Product name/URL are mutable observations, not identity.
- **evidence_span** — verbatim substring of a source observation backing a non-null trait/quantity, plus the source field name and a SHA-256 hash of that field's text.
- **preferred_comparable_unit** — the unit a leaf declares as default for basket math (required on compare leaves).
- **Normalized comparable price** — shelf price ÷ quantity in the leaf's preferred comparable unit. Derived on read; always reported with currency + unit.
- **DLQ / deferred queue** — the non-blocking review queue for `unknown`/`defer` outcomes.

## References

- https://fermisense.com/when-machines-take-the-wheel/
- [CLI > MCP](https://ejholmes.github.io/2026/02/28/mcp-is-dead-long-live-the-cli.html)
- [Cloudflare Code Mode](https://blog.cloudflare.com/code-mode/)
- Brainstorm: `_bmad-output/brainstorming/brainstorm-2026-agent-workflow-2026-07-30/`
