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
- **Traits (I3):** mandatory `evidence_span` on non-null traits; allow `unknown` / `defer` → DLQ (H2)
- **Persist (D6):** upsert **merges** LLM attributes — never wipe on re-import
- **Create/merge:** eager create during discovery (N1); periodic hygiene agent (M2) + post-bulk reconciliation (M5)
- **Human loop:** non-blocking only — async low-confidence dashboard (H1) + unknown→DLQ (H2)
- **Eval / observability MVP:** golden assign set (E1), per-stage evals (E2), token-cost-per-item (E3), model/context bakeoff (E5)
- **Portfolio showcase:** inspectable agent runs + shareable bakeoff metrics (O+P under the same harness)

### Explore under eval (not fixed yet)

- **Orchestration (O1–O5):** tool-calling, CLI-like, Code Mode, LangGraph/state-machine, hybrid — bake off; do not pre-pick
- **Product supply (P2/P3/P4/P9/P10):** one-at-a-time, embedding neighbors, agent search, hybrids, cluster-then-call — bake off

## Open questions

- Can a **product** live in multiple places? (many-to-many vs many-to-one)
- Are **categories** a **tree or a graph**?
- Category granularity default: consumer-fine vs category+facets hybrid vs hierarchy
- Unit protocol: reliability of category-level preferred unit; what overrides are allowed?
- Secondary comparable units and per-product overrides — data model impact
- Runtime unknown-vs-inferred handling beyond eval + evidence_span
- How strong is prefer-match-existing vs eager create in practice — hygiene thresholds?
- Agent run UI depth at MVP vs logs + eval only until later
- Trait extraction path: deterministic+LLM verify vs LLM-only+evidence_span
- Draft/propose categories until N products — keep as fallback or drop near-term?

## References

- https://fermisense.com/when-machines-take-the-wheel/
- [CLI > MCP](https://ejholmes.github.io/2026/02/28/mcp-is-dead-long-live-the-cli.html)
- [Cloudflare Code Mode](https://blog.cloudflare.com/code-mode/)
- Brainstorm: `_bmad-output/brainstorming/brainstorm-2026-agent-workflow-2026-07-30/`
