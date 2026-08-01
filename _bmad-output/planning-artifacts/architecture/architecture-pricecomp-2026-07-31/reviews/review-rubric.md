# Reviewer Gate — Good-Spine Rubric

**Artifact:** `ARCHITECTURE-SPINE.md`  
**Altitude:** initiative → capability/feature units  
**Verdict:** **CHANGES REQUIRED, NARROWED TO TWO LOAD-BEARING GAPS.** The revision resolves the prior stage-contract, telemetry, job/idempotency, migration, technology, CAP-8, and operational-envelope findings. Controlled experiment state and shared embedding infrastructure remain insufficiently fixed for independent feature units.

## Gate summary

- **Mechanical lint:** PASS — `lint_spine.py` reported zero findings.
- **Real divergence points:** FAIL — experiment isolation and embedding ownership are still open.
- **AD enforceability:** PASS WITH TWO EXCEPTIONS — AD-20 cannot guarantee identical experiment conditions without state isolation, and AD-2 names embedding filtering without a supporting shared contract.
- **Deferred safety:** PASS — every remaining deferred choice now has a pre-divergence revisit condition or is constrained behind AD-34.
- **Named technology currentness:** PASS — all exact stack pins matched live current releases on 2026-07-31; the Phoenix image tag exists and the named integrations support CPython 3.14.
- **Brownfield ratification/migration:** PASS — existing seams are preserved or explicitly migrated, with executable replay and cutover evidence.
- **CAP-1 through CAP-10:** PASS WITH TWO IMPLEMENTATION-CONVERGENCE GAPS — CAP-1's embedding filter and CAP-10's controlled bakeoff isolation need one more invariant each.
- **Initiative-dimension coverage:** PASS — local/CI/runtime topology is decided and all later release, configuration, backup, operations, provider/IaC, and security dimensions are explicitly gated under Deferred.

## Critical findings

None.

## High findings

### H1 — Controlled bakeoffs do not isolate mutable business state

**Evidence:** AD-20 requires workflow and supply candidates to run against identical persistence and inputs. AD-21 groups runs under one immutable ingest-selection manifest, and AD-31 says eval manifests freeze a taxonomy version. The authoritative taxonomy, catalog, enrichment, review, and comparison stores remain mutable current-state tables, however. No rule defines a restorable baseline, per-candidate database/schema, copy-on-write namespace, or reset protocol.

**Why this fails the rubric:** Discover/create and assign candidates change the taxonomy and memberships they later search. If candidate B runs after candidate A against the same owner tables, B observes categories and enrichment created by A. Both runs can satisfy every current AD while the experiment no longer compares equivalent conditions. Different implementation units may choose transaction rollback, database cloning, destructive reset, or shared-state sequential execution, producing incompatible and scientifically invalid CAP-10 results.

**Disposition:** **Discuss, then fix before eval-harness implementation.** Choose one isolation contract: restore every candidate from the same immutable database baseline, provision one isolated database/schema per candidate, or define an equivalent copy-on-write run namespace. Bind taxonomy/catalog/config snapshot identity, reset/cleanup behavior, and a test proving no candidate can observe another candidate's writes.

### H2 — Required embedding uses have no shared owner or runtime contract

**Evidence:** CAP-1 and AD-2 require filtered ingest by embedding. P3, P9, and P10 also depend on product embeddings. The spine defines no embedding owner, model/version identity, vector representation, storage/index boundary, distance semantics, refresh/invalidation rule, or reproducible tie to a catalog observation. The C4 deferral concerns category-context maturity, not CAP-1 filtering or P-strategy product supply. The selected provider adapters cover chat models only.

**Why this fails the rubric:** The filtered-ingest feature and product-supply experiments can independently introduce incompatible embedding models, stores, dimensions, similarity metrics, and lifecycle semantics. That breaks shared ingest manifests, invalidates controlled P-strategy comparisons, and can force an unreviewed infrastructure dependency despite embedding being a required capability rather than an optional maturity arm.

**Disposition:** **Discuss, then add an invariant or explicit pre-implementation gate.** Assign embedding ownership, define an immutable embedding identity `(observation revision, model/version, preprocessing version)`, select or constrain the storage/query port and distance semantics, and require CAP-1 filtering plus P-strategy candidates to consume the same versioned embedding snapshot.

## Medium findings

### M1 — Cutover uses an undeclared observation-window contract

**Evidence:** AD-15 defines behavior “during the observation window” and switches to forward-only recovery afterward, but neither the rule nor Deferred says who declares the window, when it must be fixed, or what evidence ends it.

**Why this matters:** The rollback data posture changes materially at that boundary. Deployment and product units could use different window lengths or treat gate acceptance as implicitly ending it.

**Disposition:** **Autofix.** Add a before-cutover gate that records the observation-window duration, acceptance owner, early-exit prohibition or criteria, and the exact transition to forward-only recovery.

## Low findings

### L1 — AD-33 remains primarily procedural

The kill-pile is now a clear binding negative contract, but enforcement still depends on architecture and code review. Semantic exclusions require review; machine-checkable items could additionally become architecture tests.

**Disposition:** **Defer/ignore for gate purposes.** This does not block the spine.

## Previously reported findings now closed

- **Stage divergence:** AD-34 fixes framework-free values, stage inputs/outcomes, statuses, revision semantics, and proposal-versus-receipt meaning; Deferred allows R/D/A variants only behind that contract.
- **Telemetry divergence:** AD-12 fixes `pricecomp.telemetry.v1`, required correlation fields, span hierarchy, W3C propagation, leaf-token accounting, and Phoenix contract tests.
- **Job/idempotency divergence:** AD-22 and AD-30 define the transactional producer bridge, pre-feature failure gate, fenced work states, retry policy, payload-hash idempotency, and replay semantics.
- **Technology currentness:** uv and all missing checkpoint, pool, OpenTelemetry, OpenInference, server, and Phoenix container pins are current and verified.
- **Brownfield/cutover integrity:** AD-6 and AD-15 now bind stable source identity, immutable replay manifests, conformance checks, restore testing, capability/eval/frontend gates, and rollback data posture.
- **CAP-8 enforceability:** AD-7 makes the complete taxonomy action surface mandatory; AD-17 fixes generation, fencing, and dirty-scope semantics.
- **Operational envelope:** AD-29 decides environment parity and migration order; Deferred explicitly gates CI/release, configuration/secrets, backup/recovery, operations, provider/IaC, and public security.

## Capability coverage

| Capability | Review |
| --- | --- |
| CAP-1 | Covered except that embedding-filter implementation lacks shared ownership and version semantics (H2). |
| CAP-2 | Covered; AD-34 makes separately scored stages implementation-convergent across R/D/A variants. |
| CAP-3 | Covered; rooted tree, cycle prevention, active leaf membership, facets, and parent widening are fixed. |
| CAP-4 | Covered; evidence is immutable-observation-bound and review-safe. |
| CAP-5 | Covered; quantity precedence and revision-linked comparison projection prevent stale normalization. |
| CAP-6 | Covered; searched taxonomy context and curated MCP remain command-backed. |
| CAP-7 | Covered; stable source identity, deterministic replay, and import/enrichment ownership are fixed. |
| CAP-8 | Covered; required hygiene actions and concurrency-safe review requests are explicit. |
| CAP-9 | Covered; deferred review is non-blocking, revision-aware, fenced, and domain-action capable. |
| CAP-10 | Covered in metrics, telemetry, manifests, and candidate controls, but mutable-state isolation remains unresolved (H1). |

## Initiative-dimension coverage

| Dimension | Status |
| --- | --- |
| Paradigm, package boundaries, dependency direction | Decided |
| Shared values, errors, stage outcomes, replay meaning | Decided by AD-34 |
| Catalog identity, observations, replay, absence semantics | Decided |
| Taxonomy, enrichment, review, comparison ownership/integrity | Decided |
| API/MCP/CLI behavior and lifecycle | Decided |
| Workflow, queue, checkpoint, retry, idempotency | Decided with pre-feature feasibility gate |
| Telemetry, evaluation, retention, cost accounting | Decided |
| Controlled experiment state | **Gap: isolation/reset not decided or deferred** |
| Embedding filtering and product supply | **Gap: owner/model/store/version semantics not decided or deferred** |
| Brownfield migration and cutover | Decided; observation-window declaration needs tightening |
| Local and CI environment topology | Decided |
| CI/release, configuration/secrets, backup/recovery, operations | Explicitly deferred with before-use gates |
| Production provider, scaling, pooler, IaC | Explicitly deferred before internal staging |
| External security/public exposure | Explicitly deferred; public deployment prohibited meanwhile |

## Brownfield reconciliation

The revised spine correctly treats the NestJS backend, TypeScript importer, shared database, mutable presentation-key upsert, flat taxonomy, and scalar normalization as migration inputs rather than conventions to preserve. The current CSVs expose retailer IDs inside their product URLs for Coop, Migros, Lidl, and Denner, making source-specific stable-ID extraction plausible while AD-6 correctly requires conformance and explicit failure instead of silent fallback. PostgreSQL 18, deterministic parsing, CSV streaming, and frontend OpenAPI consumption remain ratified. This rubric item passes.

## Verification notes

- Deterministic lint: zero findings.
- Live PyPI metadata matched every pinned Python package version in Stack on 2026-07-31.
- `arizephoenix/phoenix:version-19.11.1` exists; Phoenix supports a 30-day self-hosted trace-retention policy.
- Official PostgreSQL 18 container guidance confirms `/var/lib/postgresql` as the volume target.
- FastMCP documentation confirms `http_app(path="/")`, combined lifespan handling, and stateless HTTP for the mounted `/mcp` contract.
- Reviewed from scratch: revised spine and architecture memlog; canonical `SPEC.md`, spec memlog, diagrams, bakeoffs, kill pile, glossary; representative retailer CSV headers/rows and brownfield importer identity behavior.
