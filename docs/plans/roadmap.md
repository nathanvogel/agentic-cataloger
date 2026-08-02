# Roadmap — 2026 Agent Workflow

Condensed from BMAD's epics.md (2440 lines, 58 FRs, 31 NFRs, full Gherkin ACs per story — deleted) and sprint-status.yaml (also deleted). This is a prototype; the story list below is the actual build plan, not a formal requirements traceability exercise. Full technical invariants live in [../specs/architecture.md](../specs/architecture.md); scope/why in [../specs/2026-scope.md](../specs/2026-scope.md).

Status as of 2026-08-01: only Epic 1 has started.

**Scope cuts from the original BMAD plan** (see bottom of Epic 5 and Epic 6 for details): the Deferred review page loses its dedicated design-token/keyboard-nav/responsive/"hold contract" stories — it's one small read-only page, not a design system. The eval/bakeoff epic loses the full 2×2 isolated-database bakeoff machinery until one workflow shape actually works end to end — comparing variants only pays off once there's something to compare. **PgQueuer is cut from Epic 1** (2026-08-02): no durable job queue, no separate `worker` role — ingest/pipeline/hygiene run as direct, synchronous, idempotent command invocations, and LangGraph's per-node `RetryPolicy` covers flaky LLM calls. Revisit if scheduled/unattended triggering is ever wanted; see [../specs/2026-scope.md § Deferred from MVP](../specs/2026-scope.md#deferred-from-mvp-deferred-not-killed).

## Order

```text
Epic 1 (stack + ingest) ──> Epic 2 (taxonomy) ──> Epic 3 (traits/price) ──> Epic 4 (agent pipeline) ──> Epic 6 (eval)
                                                                                    └──> Epic 5 (deferred page)
```

Epic 3 doesn't need an LLM at all (extraction is deterministic-first), so comparison-ready rows for the deterministic subset can ship before any agent exists.

## Epic 1 — Runnable Python stack + non-destructive ingest

Boot `api`/`migrate` against Postgres + Phoenix, and pull products into the new catalog through one ingest primitive, without ever wiping enrichment on re-import (the D6 bug).

- [x] **1.1** Relocate legacy TypeScript under `/legacy`, seed `/backend` as the Python monolith root.
- [x] **1.2** Run the stack locally with `api`/`migrate` role commands via Compose (`worker` exists as an inert stub — not the dispatch mechanism, see the PgQueuer cut above).
- [ ] **1.3** Guard taxonomy-mutating commands (hygiene, reparent/merge) with a Postgres advisory lock for their duration, so an overlapping run fails loudly instead of racing.
- [ ] **1.4** Register immutable catalog snapshots and import products under durable source identity.
- [ ] **1.5** Ingest selection primitive — bulk / single / filtered through one code path.
- [ ] **1.6** Revisioned shelf prices (kind + one current row per kind).
- [ ] **1.7** D6 regression test: re-import never wipes enrichment-owned attributes.
- [ ] **1.8** Idempotent commands — safe to re-run a CLI invocation after a crash without duplicating effects.
- [ ] **1.9** Fresh-rebuild cutover: replay the immutable source manifest into new databases.

## Epic 2 — Substitutability taxonomy

A rooted tree an operator curates and an agent searches — exactly-one-leaf membership, comparable-unit policy on compare leaves, hygiene commands.

- [ ] **2.1** Build the rooted substitutability tree (no cycles, no graph edges).
- [ ] **2.2** Declare `preferred_comparable_unit` (+ optional secondaries) on compare leaves.
- [ ] **2.3** Assign a product to exactly one leaf, using the prose rubric + few-shot pairs for substitutability; keep import/source categories as ingest filters only.
- [ ] **2.4** Facets filter within a leaf; parent widening gated on compatible comparable units.
- [ ] **2.5** Search-backed category context, exposed as curated MCP tools over the command layer.
- [ ] **2.6** Prefer matching an existing category before creating; no draft category state.
- [ ] **2.7** Hygiene commands (merge/rename/reparent/reassign/coherence repair) + coalesced review requests + one post-bulk hygiene pass over touched categories.

## Epic 3 — Comparison-ready rows

Cited traits and quantities, normalized comparable price derived on read. Anything unknown/unconvertible/conflicting defers instead of being invented.

- [ ] **3.1** Record deferred items without blocking the pipeline (`deferred_items` table).
- [ ] **3.2** Deterministic-first trait/unit extraction (`unit` → `price_text` → name); high-confidence hits skip the LLM.
- [ ] **3.3** Cite every non-null trait with a verbatim `evidence_span` + field hash.
- [ ] **3.4** Record quantities with kind/source/evidence and the deterministic selection precedence.
- [ ] **3.5** LLM extraction through a provider-agnostic port for residual/low-confidence/empty traits, citing or deferring.
- [ ] **3.6** Derive normalized comparable price on read; always report currency + unit; fail closed on missing/unconvertible/incompatible-widening cases.
- [ ] **3.7** `comparable_unit_override` escape hatch for odd SKUs.

## Epic 4 — Staged agent pipeline, inspectable end to end

Discover/create → assign → extract as three separately-prompted, separately-scored LangGraph stages, with every run/stage/attempt durably identified and visible in Phoenix.

- [ ] **4.1** Run/stage-execution/attempt identity + the stage outcome envelope in `contracts/`.
- [ ] **4.2** Store stage outcomes durably; replay reapplies the stored outcome instead of re-calling the LLM.
- [ ] **4.3** Emit telemetry through a domain-owned port (OTel stays in adapters).
- [ ] **4.4** Discover/create, assign, and extract as three separately-prompted stages.
- [ ] **4.5** Orchestrate the stages in LangGraph; launch a run from an ingest selection.
- [ ] **4.6** Prove Phoenix joins runs end to end without double-counting cost.

## Epic 5 — Deferred page: seeing where the agent fails

One read-only web page over `deferred_items` (spec: [../specs/deferred-page.md](../specs/deferred-page.md)) plus a CLI re-drive command.

- [ ] **5.1** Read the deferred queue over the API; CLI `re-drive` command.
- [ ] **5.2** The page itself — shell, filterable/sorted rows with reason chips, in-row expand with payload + Phoenix link.
- [ ] **5.3** Shareable filter URLs; loading/empty/error/stale states.

*Cut from the original plan:* a dedicated design-token story, a dedicated keyboard-navigation story, a dedicated narrow-viewport story, and a meta-story for "holding the read-only contract." These are one page — build it once, correctly, per [deferred-page.md](../specs/deferred-page.md), instead of four separate stories about it.

## Epic 6 — Eval harness

Score the pipeline against a frozen golden set before comparing anything.

- [ ] **6.1** Freeze an eval manifest; Phoenix as the dataset/experiment home.
- [ ] **6.2** Golden assignment accuracy (E1) + per-stage scores (E2).
- [ ] **6.3** Average cost per item per stage (E3), leaf LLM spans only.

*Deferred, not cut:* comparing LangGraph control-flow shapes (explicit graph vs. hybrid) and product-supply strategies (one-at-a-time vs. agent search) in an isolated-database 2×2 bakeoff. Build once one workflow shape works end to end on real data — a controlled comparison is only worth the isolated-database machinery once there's a second arm worth comparing against. When it's time, the shapes to compare are noted in [2026-scope.md § Explore under eval](../specs/2026-scope.md#explore-under-eval-not-fixed-yet).
