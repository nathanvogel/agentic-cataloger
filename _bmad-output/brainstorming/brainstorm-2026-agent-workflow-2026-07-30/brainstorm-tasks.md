# Brainstorm → Spec Tasks — 2026 Agent Workflow

Actionable checklist from brainstorm `2026-07-30` (`.memlog.md` + `morphological-matrix.md`). Goal: finish `docs/specs/2026-scope.md` **New workflow**, then hand off to `bmad-spec`.

---

## 1. Finish / update `docs/specs/2026-scope.md` — New workflow

Write concrete bullets from session decisions (not architecture essays).

- [x] State the **product**: comparison-ready rows = substitutability category + traits + shelf price + normalized comparable price
- [x] State **near-term goal**: structured product DB (categories + traits), not shopper-facing features
- [x] Lock stack constraints: **Python monolith** + **DDD**; single backend for agent flow, REST, and data import
- [x] Describe **staged pipeline** (I9): discover/create → assign → extract (separate prompts / eval slices)
- [x] Document **ingest modes** (U1–U4): bulk / single upsert / filtered subset — **same pipeline** for all three
- [x] Document category context: agent **search** (C2); note mature lean **C4** (embed shortlist + search)
- [x] Document substitutability definition: **prose rubric + few-shot pairs** (S1+S2); comparison primitive = consumer substitutability (not retailer taxonomy)
- [x] Document trait policy: mandatory **`evidence_span`** (I3); allow **`unknown` / `defer`** → DLQ (H2)
- [x] Document persist rule: upsert **merges** LLM attributes — never wipe on re-import (D6)
- [x] Document create/merge: **eager create** during discovery (N1); **periodic hygiene agent** (M2) + **post-bulk reconciliation** (M5)
- [x] Document human loop: **non-blocking only** — async low-confidence dashboard (H1) + unknown→DLQ (H2)
- [x] Document eval/observability MVP: golden assign set (E1), separate evals per stage (E2), token-cost-per-item (E3), model/context bakeoff (E5)
- [x] Note portfolio showcase: inspectable agent runs + shareable bakeoff metrics (O+P under same harness)
- [x] Clarify terminology: **import/source category** = filter only; **substitutability category** = comparison primitive
- [x] Keep existing “Current issues” / bug notes aligned; mark D6 wipe bug as **hard requirement**, not just a known issue
- [x] Leave orchestration (O) and product supply (P) as **explore-under-eval**, not fixed choices
- [x] Add one-line architecture sketch (ingest → staged prompts → C2 context → explore O/P → validators → merge upsert → hygiene → non-blocking HITL)

---

## 2. Spec / BMad handoff prep

- [ ] Confirm `2026-scope.md` New workflow + Open questions are complete enough to start `bmad-spec`
- [ ] Point `bmad-spec` at this folder: `.memlog.md`, `morphological-matrix.md`, `brainstorm-tasks.md`
- [ ] Carry forward **MVP commitments table** (C2, S1/S2, I3/I9, D6, N1, M2/M5, E1–E3/E5, U1–U4) as assumed constraints
- [ ] Carry forward **explore set** as bakeoff design input — do not collapse into one stack in the first spec draft
- [ ] Carry forward **kill pile** as explicit out-of-scope / anti-patterns
- [ ] Note settled constraints for architect: Python monolith, DDD, security **out of scope** for this initiative
- [ ] Note generic-catalog requirement: design for non–Swiss-grocery sources with minimal adaptation
- [ ] Decide where formal specs live going forward (move off `.kiro` / standardize path) — record choice in scope or spec kickoff

---

## 3. MVP explore bakeoffs to design (O and P)

Design the eval harness before picking winners.

### Orchestration (O1–O5 — all viable; O6 killed)

- [ ] Define bakeoff dimensions: tool-calling (O1), CLI-like interface (O2), Code Mode (O3), LangGraph/state-machine (O4), hybrid graph+tools-in-stage (O5)
- [ ] Define shared success metrics: assign accuracy (E1), per-stage scores (E2), cost/item (E3), reproducibility / inspectability
- [ ] Specify minimum comparable runs (same eval set, same ingest slice) before any O* is preferred in writing

### Product / adjacent supply (P2, P3, P4, P9, P10)

- [ ] Define bakeoff candidates: one-at-a-time (P2), embedding neighbors (P3), agent search (P4), neighbors+search (P9), cluster-then-call (P10)
- [ ] Define what “good” looks like for supply: category assign quality vs tokens/item; recall of true substitutes in context
- [ ] Explicitly exclude killed supply shapes from experiments: P1, P5, P6, P7, P8

### Related explore (lock later, not now)

- [ ] Plan compare for parse path: R1 vs R2 (+ R5 retry, R6 validators)
- [ ] Plan compare for persist path: D1 agent-save vs D2 orchestrator-after-validate
- [ ] Plan compare for assign timing: A2 (after category confirmed) vs A3 (deferred batch)
- [ ] Plan compare for HITL surfaces: H1 dashboard vs H2 DLQ (both required directionally; UI depth TBD)
- [ ] Defer maturity work on C4 until C2 + eval harness exist

---

## 4. Hard commitments to lock in writing

These are decided — write them as requirements, not options.

- [ ] C2 — category context via agent search (MCP/CLI-like); no full taxonomy dump
- [ ] S1 + S2 — substitutability = prose rubric + few-shot labeled pairs
- [ ] I3 — every non-null trait has `evidence_span` (verbatim source substring); deterministic validator rejects uncited values
- [ ] I9 — separate prompts/stages for create, assign, extract
- [ ] D6 — merge upsert; re-import must not wipe LLM fields
- [ ] N1 — eager category create during discovery
- [ ] M2 + M5 — periodic taxonomy hygiene + reconciliation after each bulk import
- [ ] E1, E2, E3, E5 — eval subset first; split by stage; cost/item; model/context bakeoff
- [ ] U1–U4 — bulk, single, filtered; one pipeline
- [ ] Human-in-loop: non-blocking only (H1/H2 direction)
- [ ] Automation maximized; humans only where judgment is needed
- [ ] Security explicitly out of scope for this initiative

---

## 5. Explicit non-goals / kill pile to record

Add a short **Won’t do (MVP)** section in scope or the first spec.

- [ ] No full taxonomy / parent-subtree dumps into prompts (C1, C5); no keyword-only category match (C6)
- [ ] No whole-batch / whole-catalog / raw-source-category product dumps as primary supply (P1, P5, P6)
- [ ] No “include already-assigned DB products” as product-supply strategy (P7 — category unknown at supply time); no new-only exclude as strategy (P8)
- [ ] No pure prompt chain without tools (O6)
- [ ] No blocking wait-for-human resume (H3/H3a/H3b); no MVP with zero human loop (H4); no sample-audit-only or create/merge-only HITL as sole loop (H5, H6)
- [ ] No embedding-cluster-then-label-as-definition (S3); no price-comparability as co-criterion for category membership (S7)
- [ ] No soft token-budget hints as control (I5); no special multilingual prompt rules as MVP commitment (I6)
- [ ] No free-text brittle parse (R3); no secondary LLM extractor over free text (R4)
- [ ] No natural-text→parse→save (D3); no staging-promote tables (D4); no append-only event log as primary persist (D5)
- [ ] No same-call assign+create (A1); no human-approve-only assign (A4); no delta-only assign (A5); no soft/hard two-phase assign (A6)
- [ ] No human-gated / assign-only / search-miss-only / draft-publish create modes as MVP (N3–N6)
- [ ] No never-auto / human-only / silent name+embed auto-merge (M1, M3, M4)
- [ ] No SKU-fine, department-coarse, or price-variance-adaptive granularity as MVP defaults (G1, G3, G4)
- [ ] No “category primary unit only” (T3) as the hard unit rule

---

## 6. Open questions still unresolved

Capture in `2026-scope.md` Open questions (and resolve in `bmad-spec` / design).

- [x] Hierarchy: can a **product** live in multiple places? (many-to-many vs many-to-one)
- [x] Hierarchy: are **categories** a **tree or a graph**? (G6 viable but unsettled)
- [x] Category granularity default: consumer-fine (G2) vs category+facets hybrid (G5) vs hierarchy (G6) — which is MVP default?
- [x] Unit protocol: reliability of category-level preferred unit (T4) vs earlier “primary comparable unit required” lean; what overrides are allowed?
- [x] Secondary comparable units and per-product overrides — UX / data model impact
- [x] Runtime unknown-vs-inferred handling beyond eval + evidence_span (user open; no approach chosen)
- [x] How strong is prefer-match-existing (I7) vs eager create (N1) in practice — thresholds for hygiene?
- [x] Agent run UI depth at MVP (E4 viable) vs logs + eval only until later
- [x] Trait extraction path: deterministic+LLM verify (T1) vs LLM-only+evidence_span (T2)
- [x] Draft/propose categories until N products (N2) — keep as fallback or drop from near-term design?

---

## Done when

- [ ] `docs/specs/2026-scope.md` New workflow reflects commitments, explore set, kill pile, and open questions above
- [ ] Ready to run `bmad-spec` without re-litigating settled morph ratings
