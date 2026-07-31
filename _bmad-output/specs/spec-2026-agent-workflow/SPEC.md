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

## Capabilities

- **CAP-1**
  - **intent:** Operator can ingest products as a bulk catalog, single upsert, or filtered subset (source category / keyword / embedding) through the same pipeline.
  - **success:** All three modes produce equivalent stage outcomes on a shared ingest slice; no mode-specific agent path.
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
  - **success:** Basket math picks the quantity row matching preferred unit (or parent when widening); missing/unconvertible yields null + defer/DLQ, never a fake normalize.
- **CAP-6**
  - **intent:** Agents obtain category context by searching the taxonomy on demand rather than receiving a full (or parent-subtree) dump.
  - **success:** No prompt path dumps the full taxonomy or parent subtree; agent search (C2) is the category-context path; C4 (embed shortlist + search) is deferred maturity, not MVP blocker.
- **CAP-7**
  - **intent:** Re-import and upsert merge LLM-extracted attributes with deterministic fields and never wipe prior LLM values.
  - **success:** Re-running import on a product that already has LLM traits preserves those traits unless explicitly overwritten by a validated merge; regression test covers the D6 wipe bug.
- **CAP-8**
  - **intent:** System prefers matching an existing category before creating, creates for real when no good match (no drafts), and runs periodic plus post-bulk hygiene that can merge, rename, edit, reparent, reassign, flag for HITL, and fix leaf coherence.
  - **success:** Hygiene run demonstrates at least merge/reassign/coherence fix; no provisional/draft category state in MVP; agents consider existing membership, not only search hits.
- **CAP-9**
  - **intent:** Humans review low-confidence and deferred decisions asynchronously without blocking the pipeline.
  - **success:** Pipeline completes without waiting on a human; low-confidence items appear on an async dashboard (H1) and unknown/defer on DLQ (H2).
- **CAP-10**
  - **intent:** Operator can compare orchestration and product-supply strategies on a shared eval harness with golden assign accuracy, per-stage scores, token-cost-per-item, and model/context bakeoff metrics.
  - **success:** Same eval set + ingest slice runs for candidate O\* and P\* shapes; shareable metrics exist before any O/P winner is locked in writing.

## Constraints

- Python monolith + DDD; one backend owns agent flow, REST, and data import; Devcontainers for the environment.
- Security is out of scope for this initiative.
- Catalog design must admit non–Swiss-grocery sources with minimal adaptation.
- Substitutability definition is prose rubric + few-shot labeled pairs (S1+S2); comparison primitive is consumer substitutability, not retailer taxonomy.
- Import/source categories filter ingest only; they are not comparison primitives (see `glossary.md`).
- Unit/trait extract is deterministic-first (sources: `unit` → `price_text` → name); high-confidence deterministic success skips LLM; LLM extract only for residuals/low-conf/empty with `evidence_span` (T1). T2 is not MVP default.
- Category has `preferred_comparable_unit` + optional `secondary_comparable_units[]`; product stores `shelf_price` + `quantities[]` (qty, unit, source labeled|inferred, evidence_span; optional cached `normalized_price` on that row). Secondary normalized prices are not stored separately — use other quantity rows or derive on read. Rare `comparable_unit_override` is HITL-worthy only.
- Orchestration (O1–O5) and product supply (P2/P3/P4/P9/P10) stay in the explore set — do not pre-pick a stack in architecture or code until bakeoff metrics exist (`explore-bakeoffs.md`).
- Kill-pile options must not be built toward (`kill-pile.md`).
- Formal specs for this work live under `_bmad-output/specs/`, not `.kiro`.

## Non-goals

- Shopper-facing features (receipt upload, basket optimizer, nutrition Q&A, etc.) in this initiative.
- Security hardening / threat modeling for this initiative.
- Pre-selecting a single orchestration or product-supply stack before eval bakeoff.
- Provisional/draft categories (N2); graph / lateral “also-comparable” edges (deferred unless tree+facets fail).
- Everything listed in `kill-pile.md` (full taxonomy dumps, blocking HITL, same-call assign+create, T3 force-unit, etc.).

## Success signal

A filtered ingest slice yields comparison-ready rows (leaf category + cited traits + shelf + normalized comparable price where convertible); re-import does not wipe LLM attributes; golden assign + per-stage + cost/item metrics exist; at least two O\* and two P\* candidates have been run on the same harness with shareable numbers — with no O/P winner declared until then.

## Assumptions

- Formal-spec home is `_bmad-output/specs/` (this folder); `.kiro` is legacy for new agent-workflow work.
- Morphological matrix stays an adopted companion so morph IDs remain the shared vocabulary for bakeoffs without inlining the full matrix into the kernel.
- Runtime faithfulness beyond “evidence_span ⊆ source text” is eval-owned for MVP (no extra confidence score / second-pass verifier required).

## Open Questions

- **Category coherence timing:** Prefer-reuse (I7) is locked and agents must consider existing membership. Should coherence run per assign (every new product vs members) or only as batched reconciliation (e.g. recent + sample members)? Lean in sources: reconciliation required; per-assign full check optional/heuristic.
- **Reconciliation dirty set:** How to trigger coherence/hygiene without scanning the whole DB (category/`updated_at`, member-changed dirty flags, event queue on assign/create/reassign, audit-derived workset)?
- **Inspectability at MVP:** Custom agent-run UI (prompts, tools, writes — E4) vs structured logs + eval metrics only until later — preferring frameworks that ship inspectability before investing in a custom UI?
