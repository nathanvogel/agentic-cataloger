# Roadmap — 2026 Agent Workflow

Condensed from BMAD's epics.md (2440 lines, 58 FRs, 31 NFRs, full Gherkin ACs per story — deleted) and sprint-status.yaml (also deleted). This is a prototype; the story list below is the actual build plan, not a formal requirements traceability exercise. Full technical invariants live in [../specs/architecture.md](../specs/architecture.md); scope/why in [../specs/2026-scope.md](../specs/2026-scope.md).

**Reordered 2026-08-02 around one MVP goal: the agent creates categories and assigns products to them.** Story IDs are unchanged from the epic-ordered version (`git log docs/plans/roadmap.md`) so they still map; what changed is which ones are on the critical path. Everything not on that path moved to "After the MVP" or "Cut from the MVP line" — cut means *not now*, each with a revisit condition, same convention as [2026-scope.md § Deferred from MVP](../specs/2026-scope.md#deferred-from-mvp-deferred-not-killed).

Two facts drove the reorder:

- **Traits and normalized price aren't needed for categories.** Epic 3 was between "taxonomy" and "agent pipeline" in the old order. Nothing in discover/create or assign reads a trait, so all of Epic 3 except the deferred-items table (3.1) moves behind the MVP.
- **Solo dev, one process touching the DB, enforced by not running two commands at once.** That's a real guarantee here, so the advisory lock (1.3) and the generic idempotency-key framework (1.8) both leave the critical path. They're insurance against a concurrency story that doesn't exist yet.

## Done when

```
agentic-cataloger ingest --source-category "Milchprodukte"     # products land with stable identity
agentic-cataloger run --source-category "Milchprodukte"        # agent builds tree + assigns
agentic-cataloger taxonomy show                                # a real tree, sane leaves
agentic-cataloger deferred list                                # what it refused to guess
# and Phoenix shows two separately-scored stages per product, with cost
```

No traits, no comparable price, no web page. If that command sequence works on real Migros/Denner rows and the tree doesn't look like garbage, the MVP is done.

## Order

```text
M0 (products in)  ──> M1 (a tree to put them in) ──> M2 (the agent) ──> M3 (trust it)  ═══ MVP ═══>
                                                                                        │
                                            v0.2: eval assignment accuracy ─────────────┤
                                            v0.2: hygiene + re-drive ───────────────────┘
                                                                                        │
                                            later: traits/price (old Epic 3) ───────────┤
                                            later: deferred page (old Epic 5) ──────────┘
```

---

## M0 — Products in the database

Just enough catalog to have something to categorize.

- [x] **1.1** Relocate legacy TypeScript under `/legacy`, seed `/backend` as the Python monolith root.
- [x] **1.2** Run the stack locally with `api`/`migrate` role commands via Compose (`worker` exists as an inert stub — not the dispatch mechanism).
- [x] **1.4** Register immutable catalog snapshots and import products under durable source identity `(source_namespace, source_product_id, source_variant_id?)`. Shelf price lands as a **plain column** here — the revisioned-by-kind model (1.6) is price-comparison work, not ingest work. Import only the last csv snapshot, include and leverage new fields (documented in data/README.md) 
- [x] **1.5** Ingest filter — bulk / single / filtered through one code path. Used twice: it filters what to import *and* what a pipeline run operates on (4.5).

Upsert-on-source-identity is what makes re-import non-duplicating. That's a property of 1.4, not of the deferred idempotency framework (1.8) — don't let cutting 1.8 quietly cost you this.

## M1 — A tree to put them in

The taxonomy the agent will read and write, with no agent involved yet. All three are plain application commands, testable from the CLI.

- [x] **2.1** Build the rooted substitutability tree (no cycles, no self-parenting, no graph edges).
- [x] **2.3** Assign a product to exactly one leaf, enforced by DB uniqueness. Import/source categories stay ingest filters only. The prose rubric + few-shot pairs get written here; the agent consumes them in M2.
- [ ] **2.5** Search-backed category context over the command layer. **Hard token constraint, not an optimization** — no full-tree or subtree dump, ever. MVP exposes this to the agent as LangChain tools directly (MCP deferred).

## M2 — The agent

Two stages, separately prompted and separately scored. Extract is not one of them.

- [ ] **4.1** Define the shared vocabulary for agent runs in `contracts/` — run ID, stage ID, LLM-call ID, and a common result shape (success / defer / invalid + payload). Only discover/create and assign for now; extract comes later with 3.5.
- [ ] **3.1** `deferred_items` table — the agent needs somewhere to put "I won't guess this" before it can be allowed to refuse. Small table, unblocks everything downstream.
- [ ] **4.3** Telemetry through a domain-owned port (OTel only in adapters). Early, not last — debugging LLM stages without traces is the slowest way to build this.
- [ ] **4.4** Discover/create and assign as two separately-prompted stages. Same-call create+assign stays structurally impossible.
- [ ] **2.6** Prefer matching an existing category before creating; no draft/provisional state. This is the anti-fragmentation policy the discover stage implements.
- [ ] **4.5** Orchestrate the stages in LangGraph; launch a run from an ingest filter (1.5). Node-level `RetryPolicy` covers flaky calls.

## M3 — Trust it

- [ ] **4.6** Prove Phoenix joins a run end to end and doesn't double-count cost (leaf LLM spans only; `llm.provider` set and a matching model-pricing entry, or cost silently reads $0).
- [ ] **1.7** D6 regression test — re-import never wipes enrichment-owned state. **Scope note: at MVP, "enrichment-owned state" is the agent's category assignment.** This is exactly the legacy bug reappearing in a new shape; the test is mandatory the moment the agent writes anything.

---

## After the MVP

### v0.2 — is it any good, and can you fix it when it isn't

- [ ] **6.1** Freeze an eval manifest; Phoenix as dataset/experiment home.
- [ ] **6.2** Golden assignment accuracy (E1) + per-stage scores (E2). This is the number that tells you whether the MVP is worth anything — first thing after it runs.
- [ ] **2.7** Hygiene commands (merge/rename/reparent/reassign/coherence repair) + coalesced review requests + one post-bulk pass over touched categories. The agent *will* fragment the tree; 2.6 reduces it, hygiene repairs it.
- [ ] **5.1** Read the deferred queue over the API; CLI `deferred list` + `re-drive` against the same endpoint. Ship CLI first — the page (5.2) consumes that API, not a parallel read path.
- [ ] **1.10** Curated FastMCP adapter — thin wrapper over the same command layer 2.5 already exposes to LangChain. Same tools, different transport.

### Later — traits, price, and the review page (old Epic 3 and 5)

Everything here is unchanged in content, just moved behind the MVP.

- [ ] **3.2** Deterministic-first trait/unit extraction (`unit` → `price_text` → name); high-confidence hits skip the LLM.
- [ ] **3.3** Cite every non-null trait with a verbatim `evidence_span` + field hash.
- [ ] **3.4** Record quantities with kind/source/evidence and the deterministic selection precedence.
- [ ] **3.5** LLM extraction through a provider-agnostic port for residual/low-confidence/empty traits, citing or deferring. This is where the third stage joins the graph.
- [ ] **1.6** Revisioned shelf prices (kind + one current row per kind).
- [ ] **2.2** `preferred_comparable_unit` validation + secondaries on compare leaves — see the note below, the *column* should exist earlier.
- [ ] **2.4** Facets filter within a leaf; parent widening gated on compatible comparable units.
- [ ] **3.6** Derive normalized comparable price on read; always report currency + unit; fail closed on missing/unconvertible/incompatible-widening.
- [ ] **3.7** `comparable_unit_override` escape hatch for odd SKUs.
- [ ] **5.2** The deferred page — shell, filterable/sorted rows with reason chips, in-row expand with payload + Phoenix link (spec: [../specs/deferred-page.md](../specs/deferred-page.md)).
- [ ] **5.3** Shareable filter URLs; loading/empty/error/stale states.
- [ ] **6.3** Average cost per item per stage (E3), leaf LLM spans only.
- [ ] **4.2** Store stage outcomes durably; replay reapplies the stored outcome instead of re-calling the LLM.
- [ ] **1.9** Fresh-rebuild cutover: replay the immutable source manifest into new databases.
- [ ] **1.11** Backfill catalog from earlier CSV scraps — union by source identity across historical snapshots.

## Cut from the MVP line

Not killed — each comes back on a trigger. Same convention as the scope doc.

| Cut | Revisit when |
| --- | --- |
| **1.3** advisory lock on taxonomy-mutating commands | You run two commands at once, add a scheduler, or hand the CLI to a second person. Until then the guarantee is "don't" — which is a real guarantee for one dev on one machine, and free. |
| **1.8** idempotency keys `(command_type, caller, key)` + payload hash | Crash-mid-run recovery actually bites, or a non-CLI trigger (REST/MCP/cron) can fire the same command twice. Source-identity upsert (1.4) already covers re-running ingest. |
| **4.2** durable stage outcomes / replay without re-calling the LLM | Re-running the eval set costs real money — i.e. once 6.2 exists and the golden set is big enough to hurt. |
| **1.9** fresh-rebuild replay ceremony | Cutover is actually near. The import command *is* the replay; this story is the drill around it. |
| **2.2** required-comparable-unit validation | Comparable price is being built (3.6). See the note below — the nullable column is cheap now. |
| Old **Epic 3** (traits/quantities/price) except 3.1 | The MVP tree looks sane. Comparison-ready rows are the next product goal, not a prerequisite for categories. |
| Old **Epic 5** page (5.2, 5.3) | `deferred list` in the terminal stops being enough to see where the agent fails. |
| Full **Epic 6** eval incl. the 2×2 bakeoff | Unchanged from the previous plan: one workflow shape has to work end to end before comparing arms is worth the isolated-database machinery. Shapes to compare noted in [2026-scope.md § Explore under eval](../specs/2026-scope.md#explore-under-eval-not-fixed-yet). |

*Also still cut, from the previous revision:* PgQueuer and the separate `worker` role (2026-08-02); the deferred page's dedicated design-token / keyboard-nav / responsive / "hold contract" stories — it's one small read-only page, not a design system.

## Two notes worth acting on

**Add the `preferred_comparable_unit` column in M1, nullable, and let the create stage fill it opportunistically.** The *validation* (required on compare leaves) and every unit conversion stay deferred with 2.2/3.6. But asking the LLM "what unit does this leaf compare by?" while it's already creating the category is nearly free, and skipping it means an LLM backfill pass over every category later. Nullable column now, rules later.

**D6 grows with the agent.** Today the only enrichment-owned state is leaf membership; when 3.3 lands it's traits too. Write 1.7's regression test so it's cheap to extend, because the failure mode — re-import silently wiping AI-derived work — is the one bug this whole rebuild exists to kill.
