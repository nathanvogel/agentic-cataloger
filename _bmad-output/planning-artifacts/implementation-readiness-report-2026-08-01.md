---
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
project: pricecomp
assessmentDate: 2026-08-01
assessor: Implementation Readiness Workflow
documentInventory:
  prd:
    path: _bmad-output/specs/spec-2026-agent-workflow/SPEC.md
    note: Stands in for PRD per operator confirmation
  architecture:
    path: _bmad-output/planning-artifacts/architecture/architecture-pricecomp-2026-07-31/ARCHITECTURE-SPINE.md
    excluded:
      - architecture/architecture-pricecomp-2026-07-31/reviews/*.md
    note: Review docs excluded per operator — not used in assessment
  epics:
    path: _bmad-output/planning-artifacts/epics.md
  ux:
    design: _bmad-output/planning-artifacts/ux-designs/ux-pricecomp-2026-07-31/DESIGN.md
    experience: _bmad-output/planning-artifacts/ux-designs/ux-pricecomp-2026-07-31/EXPERIENCE.md
    mockup: _bmad-output/planning-artifacts/ux-designs/ux-pricecomp-2026-07-31/mockups/deferred-list.html
---

# Implementation Readiness Assessment Report

**Date:** 2026-08-01  
**Project:** pricecomp  
**Assessor:** Implementation Readiness Workflow

---

## Document Discovery

### Confirmed Document Set

| Type | Source | Notes |
|------|--------|-------|
| PRD (stand-in) | `_bmad-output/specs/spec-2026-agent-workflow/SPEC.md` | Canonical contract; no separate `PRD.md` |
| Architecture | `ARCHITECTURE-SPINE.md` | Reviews folder excluded from assessment scope |
| Epics & Stories | `epics.md` | 121 KB; 6 epics, 58 FRs mapped |
| UX Design | `DESIGN.md` + `EXPERIENCE.md` + `mockups/deferred-list.html` | Single-route read-only deferred surface |

### Issues Resolved at Discovery

- **PRD gap:** Resolved — `SPEC.md` confirmed as PRD stand-in.
- **Architecture reviews:** Excluded from assessment per operator (context savings).
- **UX mockup:** `mockups/deferred-list.html` confirmed; `.working/key-deferred-list.html` excluded as duplicate working copy.

---

## PRD Analysis

**Source:** `_bmad-output/specs/spec-2026-agent-workflow/SPEC.md`

### Functional Requirements

The SPEC expresses functional intent as ten capabilities (CAP-1..CAP-10). The epics document decomposes these into FR1–FR58; both inventories are recorded here.

#### CAP-1 — Unified ingest selection

**FR (CAP-1):** Operator can ingest products as bulk catalog, single upsert, or filtered subset (source category / keyword) through the same pipeline.  
**Success:** One ingest-selection primitive serves all three — bulk is empty filter, single is filter of one; no mode-specific agent path.

#### CAP-2 — Staged pipeline

**FR (CAP-2):** System runs staged discover/create → assign → extract with separate prompts and eval slices.  
**Success:** Each stage scored independently (E2); same-call create+assign impossible by design.

#### CAP-3 — Substitutability taxonomy

**FR (CAP-3):** System maintains substitutability taxonomy where each product belongs to exactly one leaf; leaves are consumer-fine for default compare; facets filter within leaf; parents widen compare scope.  
**Success:** Taxonomy is a tree; product↔leaf many-to-one; demo shows leaf compare, facet filter, parent widen.

#### CAP-4 — Cited traits

**FR (CAP-4):** System extracts structured traits where every non-null value cites verbatim `evidence_span`; unknown/defer routes to review rather than inventing.  
**Success:** Deterministic validator rejects uncited non-null traits; unknown/defer land in DLQ (H2).

#### CAP-5 — Comparable quantities and normalized price

**FR (CAP-5):** System produces comparable unit quantities and normalized prices using category `preferred_comparable_unit`, without silently fabricating conversions.  
**Success:** Basket math picks accepted quantity matching preferred unit; missing/unconvertible yields null + defer/DLQ; normalized price derived on read.

#### CAP-6 — Search-backed category context

**FR (CAP-6):** Agents obtain category context by searching taxonomy on demand rather than receiving full dump.  
**Success:** No prompt path dumps full taxonomy or parent subtree; agent search is the category-context path.

#### CAP-7 — Merge-never-wipe re-import

**FR (CAP-7):** Re-import and upsert merge LLM-extracted attributes with deterministic fields and never wipe prior LLM values.  
**Success:** Re-running import preserves LLM traits unless explicitly overwritten by validated merge; regression test covers D6 wipe bug.

#### CAP-8 — Taxonomy hygiene

**FR (CAP-8):** System prefers matching existing category before creating; creates when no good match; post-bulk hygiene can merge, rename, edit, reparent, reassign, flag for HITL, fix leaf coherence.  
**Success:** Post-bulk hygiene demonstrates merge/reassign/coherence fix; no draft category state; agents consider existing membership.

#### CAP-9 — Non-blocking human review

**FR (CAP-9):** Humans see where agent failed or deferred, asynchronously without blocking pipeline, and can re-drive items.  
**Success:** Pipeline completes without waiting; defer outcomes in `deferred_items`; read-only dashboard with stage, reason, payload, Phoenix trace link; CLI re-drive.

#### CAP-10 — Eval harness and bakeoff

**FR (CAP-10):** Operator compares control-flow and product-supply strategies on shared eval harness with golden assign accuracy, per-stage scores, average cost per item, model/context bakeoff metrics.  
**Success:** Same eval set runs for O4/O5 × P2/P4 inside LangGraph; shareable metrics before winner selection.

**Total CAPs:** 10

### Non-Functional Requirements

**NFR1 (Architecture):** Python monolith + DDD; one backend owns agent flow, REST, and data import; Devcontainers for environment.

**NFR2 (Security scope):** Security is out of scope for this initiative.

**NFR3 (Catalog portability):** Catalog design must admit non–Swiss-grocery sources with minimal adaptation.

**NFR4 (Identity):** Durable source identity is `(source_namespace, source_product_id, optional source_variant_id)`; name and URLs are mutable observations, never identity.

**NFR5 (Substitutability model):** Prose rubric + few-shot labeled pairs; comparison primitive is consumer substitutability, not retailer taxonomy.

**NFR6 (Extraction policy):** Unit/trait extract deterministic-first; LLM only for residuals with `evidence_span`.

**NFR7 (Evidence shape — MVP):** `evidence_span` = source field + verbatim substring + SHA-256 hash; byte-offset and NFC normalization out of MVP.

**NFR8 (Comparable units):** `preferred_comparable_unit` required on compare leaves; normalized price derived on read; no cache on quantity rows; no indexed comparison projection in MVP.

**NFR9 (Single-writer runtime):** One operator, one worker; advisory lock at startup; second worker exits; concurrency-safety machinery deferred.

**NFR10 (Capability surface):** MCP tools as thin adapter over command layer; O2/O3 deferred.

**NFR11 (Orchestration):** LangGraph selected; O4/O5 and P2/P4 bakeoff-gated.

**NFR12 (Observability):** Self-hosted Arize Phoenix; dedicated Postgres database; 30-day trace retention; telemetry port in domain, OTel in adapters.

**NFR13 (Cost granularity):** E3 average cost per item per stage; leaf `span_kind = 'LLM'` spans only; provider billing reconciliation per model.

**NFR14 (LLM providers):** Exactly two provider adapters in MVP.

**NFR15 (Review surface):** H1 first-party read-only; H2 `deferred_items` Postgres table; re-drive by CLI; domain writes deferred.

**NFR16 (Cutover):** Fresh rebuild by manifest replay; legacy read-only; frontend on legacy API during rebuild.

**NFR17 (Kill-pile):** Options in `kill-pile.md` must not be built.

**NFR18 (Spec home):** Formal specs under `_bmad-output/specs/`, not `.kiro`.

**Total NFRs (from SPEC constraints/non-goals):** 18

### Additional Requirements

- **Companions:** `glossary.md`, `architecture-diagrams.md`, `explore-bakeoffs.md`, `kill-pile.md` are binding contract extensions.
- **Non-goals:** Shopper-facing features, security hardening, embeddings, indexed comparison projection, snapshot completeness semantics, concurrency machinery, reviewer domain writes, periodic hygiene, REST↔MCP equivalence suite — all explicitly deferred or killed.
- **Assumptions:** Single operator/worker; morphological matrix as shared bakeoff vocabulary; runtime faithfulness eval-owned for MVP.
- **Resolved decisions:** Phoenix for inspectability; LangGraph for orchestration; post-bulk hygiene only; MVP scope reduction (2026-08-01) with showcase spine held intact.

### PRD Completeness Assessment

`SPEC.md` is a dense, preservation-validated contract with clear capabilities, success criteria, constraints, and non-goals. It is suitable as a PRD stand-in. The epics document correctly notes it decomposes CAPs into 58 finer-grained FRs cross-checked against architecture ADs. Two internal architecture contradictions (AD-34 vs scope reduction) are flagged in epics but not yet resolved in the architecture spine — see Epic Quality Review.

---

## Epic Coverage Validation

### Epic FR Coverage Extracted

All 58 FRs from `epics.md` Requirements Inventory are mapped in the FR Coverage Map:

| FR range | Epic | Domain |
|----------|------|--------|
| FR1–FR7, FR49–FR58 | Epic 1 | Ingest, runtime, cutover, bootstrap |
| FR11–FR22, FR30 | Epic 2 | Taxonomy, search, MCP tools |
| FR23–FR38 | Epic 3 | Traits, quantities, normalized price, DLQ |
| FR8–FR10, FR53–FR54 | Epic 4 | Staged pipeline, run identity, replay |
| FR39–FR40 | Epic 5 | Read-only deferred UI + CLI re-drive |
| FR41–FR48 | Epic 6 | Phoenix eval harness, 2×2 bakeoff |

Epics document self-reports: **58 FRs, 58 mapped, 0 unassigned, 0 duplicated.**

### FR Coverage Analysis (CAP → Epic trace)

| CAP | PRD Requirement (summary) | Epic Coverage | Status |
|-----|---------------------------|---------------|--------|
| CAP-1 | Unified ingest primitive | Epic 1 (FR1, FR6–FR7, FR49–FR52) | ✓ Covered |
| CAP-2 | Staged discover/assign/extract | Epic 4 (FR8–FR10, FR53–FR54) | ✓ Covered |
| CAP-3 | Substitutability tree | Epic 2 (FR11–FR16, FR30) | ✓ Covered |
| CAP-4 | Cited traits, defer to DLQ | Epic 3 (FR23–FR27, FR37–FR38) | ✓ Covered |
| CAP-5 | Normalized comparable price | Epic 3 (FR28–FR36) | ✓ Covered |
| CAP-6 | Search-backed context | Epic 2 (FR21–FR22) | ✓ Covered |
| CAP-7 | Merge-never-wipe | Epic 1 (FR6) | ✓ Covered |
| CAP-8 | Taxonomy hygiene | Epic 2 (FR17–FR20) | ✓ Covered |
| CAP-9 | Non-blocking review | Epic 3 + Epic 5 (FR37–FR40, UX-DR*) | ✓ Covered |
| CAP-10 | Eval bakeoff | Epic 6 (FR41–FR48) | ✓ Covered |

### Missing Requirements

**None.** All CAP-1..CAP-10 capabilities trace to epic stories. The 58-FR decomposition provides finer granularity with full coverage.

### Coverage Statistics

- Total PRD capabilities (CAPs): 10
- Total decomposed FRs: 58
- FRs covered in epics: 58
- Coverage percentage: **100%**
- UX Design Requirements (UX-DR1..UX-DR21): mapped to Epic 5

---

## UX Alignment Assessment

### UX Document Status

**Found.** Three artifacts confirmed:

- `DESIGN.md` — visual tokens, component specs, brand posture
- `EXPERIENCE.md` — IA, flows, behavioral rules, accessibility floor
- `mockups/deferred-list.html` — composition reference

### UX ↔ PRD Alignment

| UX requirement | SPEC / CAP alignment | Status |
|----------------|---------------------|--------|
| Read-only `deferred_items` surface | CAP-9, H1/H2 constraints | ✓ Aligned |
| Stage, reason, payload, Phoenix trace | CAP-9 success criteria | ✓ Aligned |
| Re-drive by CLI only (no UI writes) | CAP-9, H1 deferred writes | ✓ Aligned |
| No custom E4 trace UI | SPEC non-goal | ✓ Aligned |
| Security/auth out of scope | SPEC constraint | ✓ Aligned |
| Reason codes as stored (`unknown`, `defer`, `low_confidence`) | Pipeline stage vocabulary | ✓ Aligned |

`EXPERIENCE.md` explicitly reconciles CAP-9 with the 2026-08-01 scope reduction — no sync debt noted.

### UX ↔ Architecture Alignment

| UX need | Architecture support | Status |
|---------|---------------------|--------|
| Read-only deferred list API | AD-8, AD-24 (REST + MCP co-hosted) | ✓ Supported |
| `deferred_items` table schema | AD-8, review package | ✓ Supported |
| Phoenix deep links | AD-9, AD-14 observability | ✓ Supported |
| Frontend separate from monolith | AD-1, AD-15 cutover | ✓ Supported |
| URL query params for filters | Not in architecture (implementation detail) | ✓ No conflict |
| Desktop-first, light mode, English | AD-32 scope | ✓ Supported |

Architecture gate AD-8 requires binding review lifecycle details before schema/UI implementation — epics Story 5.1 addresses API shape; gate items listed in epics Additional Requirements.

### Alignment Issues

**None critical.** UX scope is intentionally minimal (single route) and fully within CAP-9.

### Warnings

- **Frontend hosting model:** Architecture defers "frontend review and category-browser details" to a gate before frontend migration. Epic 5 stories assume a read API + frontend route but do not specify whether this ships inside `frontend/` or as a standalone page — acceptable for MVP but should be bound at Epic 5 kickoff.
- **Stale list / no websocket:** UX specifies manual Refresh; architecture does not contradict; operator expectation is clear.

---

## Epic Quality Review

### Epic Structure Validation

#### User Value Focus

| Epic | Title pattern | User outcome | Verdict |
|------|---------------|--------------|---------|
| E1 | Runnable Python Stack… | Boot stack, ingest without wiping enrichment | ✓ Operator value |
| E2 | Substitutability Taxonomy… | Curate tree, agent searches | ✓ Operator value |
| E3 | Comparison-Ready Rows… | Cited traits, normalized price, defer queue | ✓ Operator value |
| E4 | Staged Agent Pipeline… | Inspectable LangGraph runs in Phoenix | ✓ Operator value |
| E5 | Deferred — Seeing Where… | Read-only failure map + CLI re-drive | ✓ Operator value |
| E6 | Eval Harness and 2×2 Bakeoff | Shareable metrics before winner | ✓ Operator value |

No pure technical-milestone epics. Story 1.1 (relocation/bootstrap) is infrastructure-heavy but framed as operator prerequisite and matches architecture AD-28 structural seed requirement.

#### Epic Independence

Documented dependency flow:

```text
E1 ──┬──> E2 ──┬──> E3 ──┬──> E4 ──> E6
     │         │         │
     └─────────┴─────────┴──> E5
```

- E1 stands alone (bootstrap + ingest).
- E2 needs E1 catalog only.
- E3 can ship deterministic subset without LLM (FR23) — explicitly documented.
- E5 can ship against deterministic deferrals before E4 populates `trace_id`.
- E4 needs E1–E3 foundations.
- E6 needs E4 for full bakeoff but eval infrastructure stories can begin earlier.

**No forward epic dependencies detected** (Epic N requiring Epic N+1).

### Story Quality Assessment

**Sampling across all 6 epics (49 stories total):**

- Stories use standard "As an operator, I want… So that…" format.
- Acceptance criteria consistently use Given/When/Then BDD structure.
- Error paths included (e.g., single-writer boot failure, missing trace, load errors).
- FR traceability maintained per epic header.

**Story sizing:** Appropriate vertical slices. Epic 5 has 12 stories for UX granularity — justified by 21 UX-DRs and portfolio-presentable craft requirements.

**Database creation timing:** Stories create tables when first needed (e.g., 1.4 snapshots, 1.5 products, 3.1 deferred_items) rather than one upfront schema dump. ✓

**Starter template:** Correctly handled — no greenfield starter; Story 1.1 implements mandatory reversible relocation per AD-28.

### Dependency Analysis

- Within-epic ordering is sequential and backward-only (1.1 → 1.2 → … → 1.11).
- No stories reference "wait for Story X.Y in a future epic" in sampled ACs.
- Epic 5 Story 5.1 (API) correctly precedes UI stories 5.3–5.11.

### Quality Violations

#### 🔴 Critical Violations

**None** — no forward epic dependencies, no epic-sized monolith stories, no uncovered CAPs.

#### 🟠 Major Issues

1. **AD-34 vs scope-reduction contradictions (pre-flagged in epics.md):**
   - **Evidence addressing:** AD-34 references UTF-8 byte offsets and NFC normalization; SPEC/AD-4 say these are out of MVP. Stories 3.3, 3.7 depend on simplified evidence shape.
   - **Taxonomy topology CAS:** AD-34 requires taxonomy-wide compare-and-set; AD-3/AD-16 say omitted under single-writer runtime.
   - **Impact:** Implementers following AD-34 literally will over-build MVP scope.
   - **Recommendation:** Amend AD-34 in `ARCHITECTURE-SPINE.md` before Epic 2/3 implementation stories begin, or add explicit story-level override citing scope reduction.

2. **Gated prerequisites not yet bound (epics Additional Requirements):**
   - Bootstrap acceptance manifest, database privilege manifest, PgQueuer completion-reliance proof, first-party review lifecycle details, telemetry join contract test.
   - **Impact:** Epic 1 Stories 1.2+ and Epic 5 Story 5.1 have implicit gates that could block mid-sprint.
   - **Recommendation:** Bind gate artifacts as checklist items at Epic 1 Story 1.1 completion or create thin binding stories.

#### 🟡 Minor Concerns

1. **Epic 1 Story count (11 stories):** Large but coherent; consider sprint boundary at 1.6 (first ingest slice) for early demo milestone.
2. **Epic 5 frontend host:** Standalone page vs `frontend/` route not specified.
3. **Version pins in NFR17:** Extremely specific dependency versions — ensure `pyproject.toml`/`uv.lock` exist at Story 1.1 completion or CI will drift immediately.

### Best Practices Compliance Checklist

| Check | E1 | E2 | E3 | E4 | E5 | E6 |
|-------|----|----|----|----|----|----|
| Delivers user value | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Independent of future epics | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Stories appropriately sized | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| No forward dependencies | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Tables created when needed | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Clear acceptance criteria | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| FR traceability | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## Summary and Recommendations

### Overall Readiness Status

**READY** for Phase 4 implementation — planning gates bound; AD-34 aligned. Remaining work is story execution (Epic 1 Story 1.1 partial relocation may already be merged).

### Unbound architecture gates — resolved 2026-08-01

Bound in [`_bmad-output/implementation-artifacts/gates/`](../implementation-artifacts/gates/):

| Gate | File | Blocks |
|------|------|--------|
| Bootstrap | GATE-01-bootstrap.md | Stories 1.1, 1.2 |
| DB privileges | GATE-02-db-privileges.md | Story 1.2 |
| PgQueuer proof | GATE-03-pgqueuer-proof.md | Story **1.2a** (spike after 1.2, before 1.4); Story 1.10 regression |
| Review lifecycle | GATE-04-review-lifecycle.md | Stories 3.1, 5.1, 5.4 |

### Critical Issues Requiring Immediate Action

1. ~~**Reconcile AD-34 with 2026-08-01 scope reduction**~~ — **resolved 2026-08-01**
2. ~~**Bind architecture gates**~~ — **resolved 2026-08-01** (decisions in gate files; implementation remains in stories)

### Recommended Next Steps

1. Patch `ARCHITECTURE-SPINE.md` AD-34 (or add explicit deferral callouts) to match SPEC constraints; re-run a quick consistency check against epics FR25 and FR50.
2. Create lightweight gate checklist documents (or stories) for bootstrap, DB roles, PgQueuer proof, and review lifecycle — attach to Epic 1 Definition of Done.
3. Begin Epic 1 Story 1.1 (relocation + Python structural seed) — this is the documented mandatory first step and unblocks all downstream work.
4. Decide Epic 5 frontend hosting (route in `frontend/` vs standalone) at Epic 5 planning, not during implementation.
5. Keep architecture review docs out of implementation context; `ARCHITECTURE-SPINE.md` + SPEC companions are sufficient.

### Strengths Observed

- SPEC as canonical contract with explicit non-goals and kill-pile negative contract.
- Epics derived directly from SPEC with transparent FR decomposition and coverage map.
- UX spine pair tightly scoped to CAP-9 with mockup reference; no scope creep into review console.
- Epic dependency graph allows incremental delivery (deterministic E3, E5 before full E4).
- BDD acceptance criteria are testable and error-aware throughout.

### Final Note

This assessment identified **2 major issues** and **3 minor concerns** across architecture consistency, gate binding, and implementation detail categories. Address the AD-34 contradictions and gate bindings before Epic 2/3; Epic 1 can proceed once gates for Stories 1.2+ are scheduled. The planning foundation is strong — these are refinement items, not fundamental gaps.

---

*Report generated: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-08-01.md`*
