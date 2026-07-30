# Morphological Matrix — 2026 Agent Workflow

Rate each option in the **Rating** column using exactly one of:

| Code     | Meaning                                           |
| -------- | ------------------------------------------------- |
| `kill`   | Drop — wrong fit, too costly, or actively harmful |
| `viable` | Acceptable later or as fallback; not preferred    |
| `mvp`    | Great for MVP / portfolio first cut               |
| `mature` | Great once system is stable / at scale            |

Leave blank until rated. Options marked _(you)_ came from you; _(coach)_ filled gaps; _(both)_ overlapped.

---

## 1. How category context is supplied

| ID  | Option                                                  | Notes                                              | Rating |
| --- | ------------------------------------------------------- | -------------------------------------------------- | ------ |
| C1  | Fetch all categories under that parent                  | Simple, risks pollution as taxonomy grows          | k      |
| C2  | Agent searches via MCP / CLI-like tools                 | Retrieval on demand; avoids full dump              | mvp    |
| C3  | Fetch categories with similar text embeddings           | Pre-filter before LLM; cheapish                    | v      |
| C4  | Hybrid: embed-similar shortlist + agent can search more | _(coach)_ Covers recall gaps of pure pre-filter    | mat    |
| C5  | Dump entire taxonomy into prompt                        | _(coach)_ Current pain point; usually bad at scale | k      |
| C6  | Keyword / fuzzy name match only (no vectors)            | _(coach)_ Simpler infra; weaker on synonyms        | k      |

## 2. How product and adjacent products are supplied

| ID  | Option                                               | Notes                                       | Rating |
| --- | ---------------------------------------------------- | ------------------------------------------- | ------ |
| P1  | Entire current batch (may be somewhat random)        | Easy batching; weak substitutability signal | k      |
| P2  | One product at a time                                | Max control / eval-friendly; costly         | v      |
| P3  | Similar products by text-embedding neighbors         | Your ~90% recall pre-process idea           | v      |
| P4  | Agent can search products on demand                  | Tool/CLI path                               | v      |
| P5  | Entire catalog of names                              | Only viable for tiny scopes                 | k      |
| P6  | All products in raw source category                  | Strong retailer-local context               | k      |
| P7  | Include existing DB products already assigned        | Helps consistency / precedent — **misframed: category unknown at supply time** | k      |
| P8  | Exclude existing DB products (new only)              | _(coach)_ Faster; more duplicate risk       | k      |
| P9  | Hybrid: embedding neighbors + agent search           | _(coach)_ Pre-filter + escape hatch         | v      |
| P10 | Cluster batch by embedding, run one call per cluster | _(coach)_ Cost/quality middle ground        | v      |

## 3. Agent-with-tools vs deterministic graph of steps

| ID  | Option                                             | Notes                                                                                                         | Rating |
| --- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------ |
| O1  | Tool-calling agent (function/MCP tools)            | Flexible; harder to eval/reproduce                                                                            | v      |
| O2  | CLI-like interface for agent + human               | Debuggable, composable; [CLI > MCP](https://ejholmes.github.io/2026/02/28/mcp-is-dead-long-live-the-cli.html) | v      |
| O3  | Code Mode (agent writes code that calls APIs)      | [Cloudflare Code Mode](https://blog.cloudflare.com/code-mode/); less schema bloat                             | v      |
| O4  | LangGraph / state-machine fixed sequence           | Deterministic stages; less “agentic” demo                                                                     | v      |
| O5  | Hybrid: graph of stages, tools only inside a stage | _(coach)_ Eval per stage + agentic where needed                                                               | v      |
| O6  | Pure prompt chain (no tools, context preloaded)    | _(coach)_ Simple; hits your current fragmentation issues                                                      | k      |

## 4. How human is looped in

| ID  | Option                                           | Notes                                      | Rating |
| --- | ------------------------------------------------ | ------------------------------------------ | ------ |
| H1  | Low-confidence dashboard (async review)          | Non-blocking; portfolio-visible            | v      |
| H2  | Unknown / defer → DLQ / review queue             | Pairs with evidence_span + unknown         | v      |
| H3  | Blocking wait-for-human, then resume             | Strongest quality; slow; solo-dev friction | k      |
| H3a | …resume with persisted run state                 | _(coach)_ Durable; more infra              | k      |
| H3b | …resume with process held in memory              | _(coach)_ Fragile; fine for demos          | k      |
| H4  | No human loop at MVP; eval + logs only           | _(coach)_ Max automation; showcase risk    | k      |
| H5  | Sample-based audit (review N% of writes)         | _(coach)_ Cost control                     | k      |
| H6  | Human only for category create/merge, not assign | _(coach)_ Gates taxonomy, not every SKU    | k      |

## 5. How consumer substitutability is defined

| ID  | Option                                                             | Notes                                         | Rating |
| --- | ------------------------------------------------------------------ | --------------------------------------------- | ------ |
| S1  | Prose rubric in system prompt                                      | _(coach)_ Fast to ship; drifts                | mvp    |
| S2  | Few-shot labeled same/not-same pairs                               | _(coach)_ Concrete; needs curation            | mvp    |
| S3  | Embedding-cluster first, LLM only labels clusters                  | _(coach)_ Cheap structure; LLM for naming     | k      |
| S4  | Human-authored policy doc agent must follow/cite                   | _(coach)_ Portfolio clarity                   | v      |
| S5  | Eval set _is_ the living definition                                | _(coach)_ Aligns with your metrics goal       | v      |
| S6  | “Would a shopper swap these for everyday purchase?” one-liner only | _(you/current)_ Minimal; ambiguous edge cases | v      |
| S7  | Price-comparability required as co-criterion                       | _(coach)_ Ties category to unit economics     | k      |

## 6. Other prompt instructions / constraints

| ID  | Option                                                     | Notes                             | Rating |
| --- | ---------------------------------------------------------- | --------------------------------- | ------ |
| I1  | Role + hard constraints only (minimal prompt)              | _(coach)_                         | v      |
| I2  | Forced reasoning / scratchpad before commit                | _(coach)_                         | v      |
| I3  | Mandatory `evidence_span` on traits                        | _(decision)_ Adopted              | mvp    |
| I4  | Explicit `unknown` / `defer` allowed outcomes              | _(you)_                           | v      |
| I5  | Soft token/cost budget hint in prompt                      | _(coach)_ Weak control            | k      |
| I6  | Multilingual rules (DE/FR/IT/EN names)                     | _(coach)_ Swiss catalogs          | k      |
| I7  | Prefer match-existing over create-new (anti-fragmentation) | _(coach)_ From reverse brainstorm | v      |
| I8  | Category unit protocol must be respected                   | _(you)_                           | v      |
| I9  | Separate prompts per stage (assign vs create vs extract)   | _(coach)_ Easier eval             | mvp    |

## 7. How agent results are parsed

| ID  | Option                                                                    | Notes                      | Rating |
| --- | ------------------------------------------------------------------------- | -------------------------- | ------ |
| R1  | Native structured output (JSON Schema / Pydantic / Zod)                   | _(coach)_                  | v      |
| R2  | Tool-call / CLI args as source of truth                                   | _(coach)_ Overlaps persist | v      |
| R3  | Free / natural text + brittle parse                                       | _(you)_ Fragile            | k      |
| R4  | Secondary LLM extractor over free text                                    | _(coach)_ Extra cost       | k      |
| R5  | Schema-fail → reject and retry                                            | _(coach)_                  | v      |
| R6  | Deterministic post-validators (evidence_span in source, unit consistency) | _(both)_                   | v      |

## 8. How agent results are persisted

| ID  | Option                                                            | Notes                                              | Rating |
| --- | ----------------------------------------------------------------- | -------------------------------------------------- | ------ |
| D1  | Agent calls explicit `save` / write action                        | _(you)_ Auditable intent                           | v      |
| D2  | Orchestrator persists structured output after validation          | _(coach)_ Safer default                            | v      |
| D3  | Agent outputs natural text that is parsed then saved              | _(you)_                                            | k      |
| D4  | Staging tables / proposed changes → promote on approve            | _(coach)_ Human loop friendly                      | k      |
| D5  | Append-only event log of agent decisions, then project to tables  | _(coach)_ Observability showcase; over-eng for now | k      |
| D6  | Upsert must merge attributes (never wipe LLM fields on re-import) | _(you/bug)_ Required regardless of path            | mvp    |

## 9. When product assignment happens

| ID  | Option                                             | Notes                                 | Rating |
| --- | -------------------------------------------------- | ------------------------------------- | ------ |
| A1  | Same call as category create/match                 | _(coach)_ Current-style; hard to eval | k      |
| A2  | Only after category exists / is confirmed          | _(coach)_                             | v      |
| A3  | Deferred batch assign after discovery pass         | _(coach)_                             | v      |
| A4  | Only after human approve                           | _(coach)_                             | k      |
| A5  | Incremental on re-import delta only                | _(coach)_                             | k      |
| A6  | Two-phase: soft assign (proposed) then hard assign | _(coach)_                             | k      |

## 10. When category creation happens

| ID  | Option                                             | Notes                              | Rating |
| --- | -------------------------------------------------- | ---------------------------------- | ------ |
| N1  | Eagerly during discovery                           | _(coach)_                          | mvp    |
| N2  | Propose-only until threshold N products would join | _(coach)_ Anti-fragmentation       | v      |
| N3  | Human-gated create                                 | _(coach)_                          | k      |
| N4  | Assign-only mode — never create                    | _(coach)_ Good for mature taxonomy | k      |
| N5  | Create only if category search returns no match    | _(you/coach)_                      | k      |
| N6  | Create as draft; publish after hygiene pass        | _(coach)_                          | k      |

## 11. When / if category merging happens

| ID  | Option                                               | Notes           | Rating |
| --- | ---------------------------------------------------- | --------------- | ------ |
| M1  | Never automatic                                      | _(coach)_       | k      |
| M2  | Periodic taxonomy-hygiene agent                      | _(coach)_       | mvp    |
| M3  | Human-triggered only                                 | _(coach)_       | k      |
| M4  | Auto when name + embedding collide                   | _(coach)_ Risky | k      |
| M5  | Reconciliation pass after each bulk import           | _(coach)_       | mvp    |
| M6  | Merge suggestions queued to review UI (never silent) | _(coach)_       | v      |

## 12. How granular should categories be

| ID  | Option                                              | Notes                                              | Rating |
| --- | --------------------------------------------------- | -------------------------------------------------- | ------ |
| G1  | SKU-fine (cherry tomato vs beefsteak)               | _(coach)_ High precision; sparse cells             | k      |
| G2  | Consumer-fine (fresh tomato)                        | _(you)_ Everyday substitutability                  | v      |
| G3  | Department-coarse (vegetables)                      | _(coach)_ Too coarse for price compare             | k      |
| G4  | Adaptive: finer where price variance is high        | _(coach)_                                          | k      |
| G5  | Category + facets hybrid (Galaxus-like)             | _(you/coach)_ Traits as facets, not new categories | v      |
| G6  | Hierarchy: coarse parent + fine leaf for comparison | _(coach)_ Open Q: tree vs graph                    | v      |

---

## Bonus axes (not in your original list — rate or ignore)

### B. Trait / unit extraction policy

| ID  | Option                                                             | Notes                         | Rating |
| --- | ------------------------------------------------------------------ | ----------------------------- | ------ |
| T1  | Deterministic at import + LLM verify                               | Split today; may waste tokens | v      |
| T2  | LLM-only with evidence_span                                        |                               | v      |
| T3  | Category defines primary comparable unit; products convert into it |                               | k      |
| T4  | Per-product unit allowed; category has preferred unit              | UX tricky                     | v      |
| T5  | Unknown unit → defer to review queue                               |                               | v      |

### C. Eval / observability placement

| ID  | Option                                               | Notes                      | Rating |
| --- | ---------------------------------------------------- | -------------------------- | ------ |
| E1  | Golden set for category assign only (first slice)    | Matches “subset is enough” | mvp    |
| E2  | Separate evals: assign / create / traits / units     |                            | mvp    |
| E3  | Token-cost-per-item tracked as first-class metric    |                            | mvp    |
| E4  | Agent run UI: inspect prompts, tools, writes         | Portfolio                  | v      |
| E5  | Compare models + context strategies on same eval set | Core showcase goal         | mvp    |

### D. Ingest mode (from 2026-scope)

| ID  | Option                                                  | Notes            | Rating |
| --- | ------------------------------------------------------- | ---------------- | ------ |
| U1  | Bulk full catalog                                       |                  | mvp    |
| U2  | Single product upsert                                   |                  | mvp    |
| U3  | Filtered subset (source category / keyword / embedding) |                  | mvp    |
| U4  | Same pipeline for all three modes                       | Generic showcase | mvp    |

---

## Combination scratchpad (non-exclusive)

Options are **not mutually exclusive**. Use this as commitments vs explore budget, not a single stack pick.

### MVP commitments (`mvp`) — ship / assume true

| Area | IDs | Reading |
|------|-----|---------|
| Category context | **C2** | Agent search via MCP/CLI-like tools |
| Substitutability | **S1, S2** | Prose rubric + few-shot pairs (both) |
| Prompt constraints | **I3, I9** | evidence_span + separate prompts per stage |
| Persist | **D6** | Upsert merges attributes (fix wipe bug) |
| Category create | **N1** | Eager during discovery |
| Category merge | **M2, M5** | Periodic hygiene agent + post-bulk reconciliation |
| Eval / observability | **E1, E2, E3, E5** | Assign golden set → split evals → cost/item → model/context bakeoff |
| Ingest | **U1–U4** | Bulk + single + filtered, same pipeline |

### MVP explore set (`viable`) — compare in evals, don’t pre-pick one

| Area | IDs | Why explore |
|------|-----|-------------|
| Orchestration | **O1–O5** | Entire tool/CLI/Code Mode/graph/hybrid space left open; only O6 killed |
| Product supply | **P2, P3, P4, P9, P10** | One-at-a-time, neighbors, agent search, hybrids, cluster batches |
| Human loop | **H1, H2** | Async dashboard + unknown→DLQ (all blocking/no-HITL killed) |
| Parse | **R1, R2, R5, R6** | Structured out, tool/CLI args as SoT, retry, deterministic validators |
| Persist path | **D1, D2** | Agent save vs orchestrator-after-validate |
| Assign timing | **A2, A3** | After category confirmed vs deferred batch |
| Granularity | **G2, G5, G6** | Consumer-fine, facets hybrid, hierarchy |
| Traits/units | **T1, T2, T4, T5** | Det+verify vs LLM-only; preferred unit; defer unknown |
| Other | **C3, I1, I2, I4, I7, I8, S4, S5, S6, N2, M6, E4** | Fallback / enrich without locking architecture |

### Mature lean (`mature` / `mat`)

| Area | IDs | Reading |
|------|-----|---------|
| Category context | **C4** | Embed shortlist + agent can search more |

### Kill pile — do not build toward

C1, C5, C6 · P1, P5, P6, P7, P8 · O6 · H3/H3a/H3b, H4, H5, H6 · S3, S7 · I5, I6 · R3, R4 · D3, D4, D5 · A1, A4, A5, A6 · N3, N4, N5, N6 · M1, M3, M4 · G1, G3, G4 · T3

### Resolved loose ends

| ID | Call |
|----|------|
| **P7** | **kill** — category unknown at product-supply time; “include already-assigned” assumes a category you don’t have yet. Precedent for *existing* categories comes via **C2** search (and later **C4**), not via dumping assigned siblings. |
| **R2** | **viable** — tool/CLI args as source of truth stays in explore set with R1/R5/R6 |

### Implied architecture sketch (commitments only)

```
ingest (U1–U4, same pipeline)
  → staged prompts (I9): discover/create (N1) | assign | extract
  → category context via agent search (C2); mature adds embed shortlist (C4)
  → product context: EXPLORE (P*) under eval (E1/E2/E5)
  → orchestration: EXPLORE (O1–O5) under same eval harness
  → traits: evidence_span (I3) + validators (R6); unknown→DLQ (H2)
  → persist: merge upsert (D6); write path EXPLORE D1 vs D2
  → taxonomy hygiene: M2 + M5; merge suggestions UI later (M6)
  → human: non-blocking only (H1/H2)
```

## Notes / conflicts:

- Orchestration (O) and product supply (P) are the main **eval bakeoff** dimensions for the portfolio showcase.
- Eager create (N1) + kill “create only if search misses” (N5) sits in tension with anti-fragmentation — hygiene (M2/M5) and prefer-match (I7 viable) carry that load.
- Kill T3 (category-primary unit only) while keeping T4 viable — unit protocol is softer than earlier first-principles lean.
- P7 killed: at supply time category is unknown; category precedent is via search (C2/C4), not assigned siblings.
- R2 confirmed viable.
