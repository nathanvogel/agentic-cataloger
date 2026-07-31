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
  - Specific subsets of the dataset (by imported category, by keyword, by embedding similarity, etc.)
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

**Stack:** Python monolith + DDD; one backend for agent flow, REST, and data import. Devcontainers setup.

**Pipeline (same for all ingest modes):** bulk / single upsert / filtered subset → staged prompts (discover/create → assign → extract) → category context via agent search (C2; mature lean: embed shortlist + search, C4) → explore orchestration (O) and product supply (P) under eval → validators → merge upsert → hygiene → non-blocking HITL.

### Commitments

- **Ingest:** bulk, single, filtered subset — **same pipeline** for all three
- **Stages (I9):** separate prompts / eval slices for discover/create, assign, extract
- **Category context (C2):** agent search (MCP/CLI-like); no full taxonomy dump. Mature: C4
- **Substitutability (S1+S2):** prose rubric + few-shot pairs; comparison primitive = consumer substitutability
- **Traits (I3):** mandatory `evidence_span` on non-null traits; allow `unknown` / `defer` → DLQ (H2). Runtime faithfulness beyond span-in-source left to eval for now (no extra confidence/second-pass MVP requirement).
- **Persist (D6):** upsert **merges** LLM attributes — never wipe on re-import
- **Create/merge:** prefer match-existing before create (I7); eager create only when no good match (N1); periodic hygiene agent (M2) + post-bulk reconciliation (M5). **No provisional/draft categories (N2)** in MVP — create for real or not at all; anti-fragmentation via I7 + hygiene.
- **Hygiene ops (M2/M5):** not merge/delete only — also rename, edit, reparent/move (incl. create parent), reassign products, and flag products for re-triage / HITL. Includes **category coherence**: review a leaf’s member products and fix bad assigns / splits / merges — not only cross-category duplicate detection.
- **Taxonomy shape:** product ↔ substitutability category is **many-to-one at the leaf** (not many-to-many). Categories form a **tree** for MVP (not a graph). Graph / lateral “also-comparable” edges deferred unless tree+facets cannot express recurring cross-branch cases.
- **Granularity (G2+G5+G6):** consumer-fine **leaves** for default compare; **facets** for within-leaf filters (organic, fat%, …); **parents** for widen-scope compare (e.g. fresh vs UHT via parent `cow milk`). Rule of thumb: separate leaf if shoppers would not silently swap; facet if same class / preference filter; parent if useful only to widen.
- **Units (T4+T5):** category has `preferred_comparable_unit` (required on compare leaves) + optional `secondary_comparable_units[]`. Product stores `shelf_price` + `quantities[]` (each: qty, unit, source labeled|inferred, evidence_span; optional cached `normalized_price` = shelf/qty nested on that row). Default basket math picks the row matching preferred (leaf, or parent when widening). Missing/unconvertible → null + defer/DLQ — no silent fake normalize. Rare `comparable_unit_override` only when preferred is nonsense for that SKU (HITL-worthy). T3 (force all into category unit) killed. Secondary normalized prices are not stored separately — use other quantity rows / derive on read.
- **Unit/trait extract (T1):** deterministic first (extend sources: `unit` → `price_text` → name); **on high-conf success skip LLM** (no always-verify — that would not beat T2 on tokens). LLM extract stage only for residuals / low-conf / empty, with `evidence_span`; unknown → DLQ. Fixable parser gaps (bare unit words, alt count vocab, Denner `(qty unit)` in price_text) are deterministic work. T2 (LLM-only) not MVP default.
- **Human loop:** non-blocking only — async low-confidence dashboard (H1) + unknown→DLQ (H2)
- **Eval / observability MVP:** golden assign set (E1), per-stage evals (E2), token-cost-per-item (E3), model/context bakeoff (E5)
- **Portfolio showcase:** inspectable agent runs + shareable bakeoff metrics (O+P under the same harness)

### Explore under eval (not fixed yet)

- **Orchestration (O1–O5):** tool-calling, CLI-like, Code Mode, LangGraph/state-machine, hybrid — bake off; do not pre-pick
- **Product supply (P2/P3/P4/P9/P10):** one-at-a-time, embedding neighbors, agent search, hybrids, cluster-then-call — bake off

## Open questions

- **Category coherence timing:** Prefer-reuse (I7) is locked; agents must consider existing category membership, not only category search hits. Open: run coherence **per assign** (every new product checks against members) vs **batched reconciliation** (e.g. 5 recent + sample of existing members, holistic pass — likely cheaper). Lean: reconciliation agent required; per-assign full check optional/heuristic.
- **Reconciliation dirty set:** How to trigger coherence / hygiene without scanning the whole DB? Candidates: category/`updated_at` timestamps, “members changed” dirty flags, event queue on assign/create/reassign, audit-log derived workset. Unsettled — pick in design/spec.
- **Inspectability at MVP:** Still pending. Build our own agent-run UI (prompts, tool calls, writes — E4) vs structured logs + eval metrics only until later. Factor: some agent vendors already ship run/trace UIs — prefer frameworks that give inspectability “for free” before investing in a custom UI.

## References

- https://fermisense.com/when-machines-take-the-wheel/
- [CLI > MCP](https://ejholmes.github.io/2026/02/28/mcp-is-dead-long-live-the-cli.html)
- [Cloudflare Code Mode](https://blog.cloudflare.com/code-mode/)
- Brainstorm: `_bmad-output/brainstorming/brainstorm-2026-agent-workflow-2026-07-30/`
