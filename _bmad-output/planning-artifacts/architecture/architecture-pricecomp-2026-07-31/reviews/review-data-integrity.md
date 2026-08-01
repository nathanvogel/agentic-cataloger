# Reviewer Gate — Data Integrity Lens, Revision 2

## Verdict

**FAIL — substantially improved, but two critical current-state eligibility/freshness invariants remain open.** The revised spine closes the original source-identity, replay-ordering, quantity-row cache, coalesced-generation, idempotency, retry, queue-enlistment, and cutover holes. It still permits historically valid enrichment or projection rows to be served after the catalog or taxonomy revision that made them current has changed.

## Review basis

This pass was performed from scratch against:

- the revised `ARCHITECTURE-SPINE.md`;
- the synchronized `SPEC.md`, `glossary.md`, and `architecture-diagrams.md`;
- the current PostgreSQL schema and TypeScript importer;
- representative Migros, Lidl, Coop, and Denner source rows.

The legacy implementation remains useful only as negative evidence and a conformance input. The revised architecture now explicitly rejects its mutable `(name, supermarket, product_url)` identity, attribute-replacement upsert, binary-float normalized values, unsorted replay, and transaction-counting behavior.

## Controls now adequately adopted

These former findings are closed and are not repeated as unresolved findings:

- durable source identity is now `(source_namespace, source_product_id, optional source_variant_id)`, with mutable names and URLs treated as observations;
- immutable checksum-addressed snapshots, deterministic replay ordering, newer-only replacement, collision handling, and explicit absence policy are adopted;
- every accepted deterministic or inferred trait and quantity now has revision-bound evidence;
- quantity kind distinguishes package content, item count, and price basis;
- normalized price no longer lives as a naked quantity-row cache and is derived from exact shelf-price and quantity revisions;
- taxonomy membership has an explicit comparison-ineligible unassigned/deferred state;
- taxonomy review generations now have bounded trigger union, generation compare-and-set, fencing, and complete dirty-scope rules;
- command writes carry expected revisions and include idempotency, projection invalidation, and dispatch in one Unit of Work;
- idempotency is payload-bound, scoped, atomic, and retained beyond queue/checkpoint replay;
- stage attempts record immutable configuration and a durable result before one-time command application;
- PgQueuer transaction enlistment is a pre-feature test gate, not a production-afterthought;
- importer conformance explicitly excludes known legacy transaction bugs;
- side-by-side cutover now uses an immutable manifest, stable source reconciliation, a restore/routing rehearsal, and an explicit forward-only point.

## Critical findings

### DI2-C1 — Revision-bound evidence can remain active after a newer catalog observation

**Evidence.** AD-4 binds every accepted trait and quantity to an immutable observation. AD-14 rejects a command whose expected catalog revision is already stale. AD-6 correctly prevents import from writing enrichment state, and CAP-7 preserves prior enrichment. No rule determines whether an enrichment revision supported by observation `N` remains eligible after observation `N+1` becomes current.

**Silent failure.** A quantity or trait can be perfectly evidenced against historical text and still be wrong for the current product. For example:

- a package changes from 500 g to 450 g;
- an organic claim disappears from the name;
- a multipack count changes;
- a variable-weight price basis replaces fixed net content.

If extraction for `N` committed before import `N+1`, optimistic stale-write rejection never runs. Owner separation then preserves the old value as designed. A comparison or facet query can continue serving it unless every reader independently remembers to compare evidence observation to the current observation.

**Required correction.** Add one current-eligibility invariant:

- an enrichment revision is current only when its evidence basis is the current catalog observation, or when a durable carry-forward/revalidation record proves that the relevant source-field hashes are unchanged between observations;
- advancing the current catalog observation must atomically make unsupported enrichment ineligible for current reads and enqueue re-drive;
- preserving history must not preserve current eligibility;
- the mechanism must respect ownership, either through a cross-owner command using owner repositories or through an authoritative revision predicate that every current query and projection enforces;
- trait, quantity, facet, and comparison reads must all use the same predicate.

Test price-only change, relevant-field change, irrelevant-field change, concurrent extraction/import, and replay of an older observation.

**Disposition:** amend AD-4, AD-6, AD-13, and AD-14 before catalog/enrichment schema design.

### DI2-C2 — The projection records derivation revisions but does not define when a row is safe to serve

**Evidence.** AD-4 and the SPEC require a revision-linked indexed comparison projection. AD-14 transactionally writes projection invalidation. AD-13 says current comparison reads use the projection. The listed projection lineage covers shelf-price revision, quantity revision, category scope, comparable unit, and formula version, but it does not require current membership revision, comparable-unit-policy revision, unit-registry revision, or a serving predicate against authoritative current state. Rebuild publication semantics are also unspecified.

**Silent failure.** A numerically correct old row can remain index-visible after:

- product reassignment to another leaf;
- leaf reparenting;
- a preferred comparable unit change;
- unit-conversion registry correction;
- reviewed quantity supersession;
- a new current catalog observation;
- a rebuild that has populated only part of the target set.

Writing an invalidation record in the owner transaction is insufficient if the indexed query does not exclude invalidated rows. A bulk delete/reinsert rebuild can expose a partial generation.

**Required correction.** Define the projection as a fail-closed current read model:

- each row carries product/catalog observation, shelf-price, quantity, membership, comparable-unit-policy, unit-registry, and formula revisions;
- owner mutation synchronously deletes/invalidates prior serveability in the same Unit of Work;
- indexed queries return a row only when its complete revision tuple matches the authoritative current tuple or a transactionally maintained current-generation pointer;
- asynchronous lag yields no comparison row, never the previous row;
- one current row is unique for the declared product/leaf/unit/currency/price-kind scope;
- rebuild writes a shadow generation and publishes it with one atomic generation switch after completeness/invariant checks;
- stale rebuild workers use expected revisions and cannot republish an older generation.

**Disposition:** amend AD-4, AD-13, AD-14, AD-23, and the projection seed before comparison persistence work.

## High findings

### DI2-H1 — Shelf-price selection remains ambiguous

**Evidence.** The model now revisions shelf prices and ties projection rows to exact price revisions, but no rule chooses the authoritative price revision. Current source data includes discounts, regular/original price text, per-unit prices, and snapshots at different times.

**Failure mode.** Two valid shelf-price revisions can represent promotional and regular prices, overlapping validity, or distinct price kinds. Different implementations can project different prices while each cites an exact revision.

**Required correction.** Define price kind, observed/effective interval, promotion precedence, currency, current-row uniqueness, and deterministic selection. Conflicting simultaneously effective prices must defer rather than use repository order. Projection identity must include the selected price kind.

**Disposition:** amend AD-4/AD-30 before shelf-price schema design.

### DI2-H2 — Optional variant identity has unsafe default SQL uniqueness semantics

**Evidence.** `SourceIdentity` contains an optional `source_variant_id`; AD-23 requires natural/current uniqueness but does not define nullable-key behavior. PostgreSQL ordinary unique constraints treat nulls as distinct.

**Failure mode.** Multiple rows with the same `(source_namespace, source_product_id, NULL)` can be inserted while the schema appears to have the required unique constraint.

**Required correction.** Require `UNIQUE NULLS NOT DISTINCT`, a non-null canonical sentinel/value object, or separate partial unique constraints for variant and non-variant identities. Add concurrent duplicate-insert tests.

**Disposition:** amend AD-6/AD-23/AD-34.

### DI2-H3 — Snapshot completeness is not restricted by ingest mode or source scope

**Evidence.** AD-2 unifies bulk, single, and filtered ingest. AD-6 permits absence handling only for a complete snapshot, but does not say who may attest completeness or whether completeness is whole-source or scoped.

**Failure mode.** A single-item or filtered ingest accidentally marked complete can deactivate every omitted product under an otherwise valid absence policy. A category-scoped source export can be mistaken for a full retailer catalog.

**Required correction.** Only a versioned source adapter performing an enumerated full scope may attest completeness. Persist the declared scope and expected/observed cardinality. Single and filtered modes are always incomplete unless the adapter proves completeness for an explicit isolated source partition; absence applies only inside that partition.

**Disposition:** amend AD-2/AD-6.

### DI2-H4 — Source identity policy evolution and retailer ID reuse have no continuity protocol

**Evidence.** AD-6 gives each adapter a versioned normalization policy and rejects missing/colliding IDs. It does not define migration when a new adapter version extracts a different ID for the same product, nor detection when a retailer reuses an old ID for a materially different product.

**Failure mode.** A normalization upgrade can duplicate the catalog and detach old enrichment. ID reuse can do the reverse: retain old membership and traits on a new SKU under the same external identifier.

**Required correction.** Add source-identity aliases/supersession and a reviewed merge/split/rekey command. Adapter upgrades require a dry-run identity diff and explicit migration map. Define semantic discontinuity checks that quarantine suspicious stable-ID reuse instead of automatically carrying current eligibility forward.

**Disposition:** amend AD-6/AD-13 and cutover conformance.

### DI2-H5 — Concurrent taxonomy topology changes need one serialization invariant

**Evidence.** AD-3 requires one rooted acyclic tree. AD-14 carries expected taxonomy revisions. AD-23 enforces locally expressible constraints. The spine does not identify whether topology commands compare one global topology revision, lock ancestor paths, or use another serializable protocol.

**Failure mode.** Two reparent commands can each validate against a non-cyclic snapshot and jointly create a cycle. Adding a child to an occupied leaf can make existing memberships point to a non-leaf between independently implemented repair steps.

**Required correction.** Bind one race-safe topology protocol: a taxonomy-wide monotonic topology revision with compare-and-set, serializable topology transaction, or documented lock order over affected paths. Leaf-to-parent conversion, reparent, merge, and delete must atomically preserve root, acyclicity, membership eligibility, dirty scopes, and projection invalidation.

**Disposition:** amend AD-3/AD-7/AD-14.

### DI2-H6 — Trait and facet compatibility is not revision-bound to taxonomy membership

**Evidence.** AD-13 assigns trait/facet definitions to taxonomy and trait revisions to enrichment. AD-25 versions trait schemas. No rule binds an active product trait to the applicable trait-definition/schema revision or invalidates it after reassignment, merge, or schema edit.

**Failure mode.** A trait valid in one leaf can remain active after reassignment to a leaf where its type or meaning differs. Facet queries can silently include products using obsolete definitions.

**Required correction.** Trait values must reference stable definition and schema revisions. Current eligibility must require compatibility with the current membership/schema revision or an explicit migration. Taxonomy mutations must atomically invalidate affected facet/projection eligibility and schedule revalidation.

**Disposition:** amend AD-4/AD-7/AD-13/AD-25.

### DI2-H7 — Reviewed overrides conflict with the canonical evidence requirement

**Evidence.** CAP-4 says every non-null trait cites evidence and its validator rejects uncited values. AD-8 allows a human value to be an explicit reviewed override without saying that the override is excluded from active traits or comparison-ready state.

**Failure mode.** One implementation treats reviewed overrides as active uncited traits, weakening CAP-4; another stores them only as review proposals. Both satisfy AD-8’s current wording.

**Required correction.** Choose one contract. Either every active trait still requires source evidence and an uncited override remains non-comparison-ready, or the SPEC must explicitly introduce reviewed overrides as a stated exception with display, audit, and eligibility semantics. Do not leave this as a privileged bypass.

**Disposition:** reconcile AD-8 with SPEC CAP-4 before review commands.

### DI2-H8 — A provider-response reference is not durable stage outcome storage

**Evidence.** AD-21 permits recording a “validated outcome or provider response reference” before one-time command application. Phoenix raw traces have 30-day retention, and provider responses are not an application-owned durable store.

**Failure mode.** A crash can leave an unapplied stage attempt whose only response reference has expired, is inaccessible, or does not preserve the exact validated structured outcome. Retry then either cannot apply or makes a new model call, violating replay semantics.

**Required correction.** Application Postgres must durably store the validated stage outcome needed for command application, with request fingerprint and config IDs. Phoenix/provider IDs may be supplemental provenance only. Retention must cover replay and audit requirements.

**Disposition:** amend AD-21/AD-34.

### DI2-H9 — Numeric sorting across currencies is not prohibited

**Evidence.** The architecture deliberately admits non-Swiss sources, uses ISO 4217, and stores currency in projection rows. No FX capability is adopted.

**Failure mode.** A parent or leaf query can numerically sort CHF, EUR, and other currency amounts together and present the smallest number as cheapest.

**Required correction.** Comparison queries must partition/filter by identical currency unless an explicit versioned FX conversion capability is later adopted. Mixed-currency requests must return structured incompatibility, not an ordered comparison.

**Disposition:** amend AD-30 and the comparison query contract.

## Medium findings

### DI2-M1 — Snapshot ordering is deterministic but its total-order token is underspecified

**Evidence.** AD-6 identifies a snapshot by source-observed time, checksum, adapter version, and completeness, and allows replacement only when newer. Current file timestamps have minute precision and are parsed in host-local time by the legacy importer.

**Risk.** Independent adapters can disagree on timezone or on ordering two distinct snapshots with the same observed timestamp. Including checksum in identity does not define which conflicting snapshot is newer.

**Required correction.** Define a source-scoped total ordering token and timezone interpretation. Equal order with different checksum is a quarantined conflict, not an arbitrary lexical winner. Adapter conformance must run identically in different host timezones.

**Disposition:** tighten AD-6/AD-30.

### DI2-M2 — Evidence offset encoding is not part of the shared contract

**Evidence.** AD-4 records field, span, offsets, and text hash; AD-34 owns `EvidenceRef`. It does not define whether offsets count UTF-8 bytes, Unicode scalar values, grapheme clusters, or normalized text.

**Risk.** Python, PostgreSQL, frontend JavaScript, and source adapters can highlight or validate different substrings for accented or composed text while sharing the same numeric offsets.

**Required correction.** Define source text normalization and offset units in `contracts/v1`; validators must re-slice and compare the exact verbatim span under that convention.

**Disposition:** add to AD-34 contract requirements.

### DI2-M3 — Cutover reconciliation can pass with field-level importer drift

**Evidence.** AD-15 gates on source ID, counts, and latest observations, plus broad invariant/eval reports. AD-6 tests normalization and committed counts. It does not explicitly require deterministic imported-fact hashes per source identity.

**Risk.** New and legacy rows can reconcile by identity/count/latest timestamp while price text, category, unit, discount, or image fields differ because of parser/normalizer drift.

**Required correction.** The immutable replay manifest should produce per-identity canonical imported-fact hashes and a reviewed field-level diff. Expected intentional differences must be allowlisted by adapter/conformance version.

**Disposition:** tighten AD-6/AD-15 acceptance evidence.

### DI2-M4 — Deferred review lifecycle remains a deliberate pre-implementation hole

**Evidence.** Deferred explicitly postpones uniqueness/coalescing, transition table, retry/cancel rules, re-drive target, and evidence promotion until before review schema/UI implementation.

**Risk.** If stories are cut directly from AD-8 without resolving this item, duplicate deferred rows and conflicting reviewer actions can still occur.

**Required correction.** Keep this as a hard story-entry gate. Its result must specify natural uniqueness, monotonic/fenced transitions, terminal reopening, duplicate trigger coalescing, and exact re-drive target revision.

**Disposition:** acceptable Deferred item only while review schema/UI implementation remains blocked on it.

## Revised gate closure criteria

The data-integrity lens can pass after:

1. current trait/quantity eligibility is explicitly invalidated or revalidated when catalog observation advances;
2. projection serveability is tied to the complete current revision tuple and rebuild publication is atomic/fail-closed;
3. shelf-price selection and price-kind precedence are deterministic;
4. nullable variant identity has enforceable uniqueness;
5. snapshot completeness authority is restricted by ingest mode and source scope;
6. source-ID policy upgrades and retailer ID reuse have explicit continuity handling;
7. taxonomy topology changes use one race-safe serialization protocol;
8. trait/facet values are schema- and membership-revision compatible;
9. reviewed-override eligibility is reconciled with CAP-4;
10. validated stage outcomes are application-durable, not external references;
11. mixed-currency comparisons fail closed.

## Required integrity tests

- Advance a catalog observation after traits and quantities are accepted; only revalidated/carry-forward values remain current.
- Change price, quantity, membership, preferred unit, unit registry, and formula independently; each old projection row becomes unservable in the same commit.
- Kill and restart a shadow projection rebuild at every phase; readers see either the old complete valid generation or the new complete generation, never a mixed one.
- Insert concurrent source identities with absent variants; exactly one row commits.
- Attempt to mark single/filtered ingest complete; absence deactivation is rejected outside its declared complete scope.
- Upgrade an adapter identity policy and simulate retailer ID reuse; unchanged products migrate once and discontinuities quarantine.
- Run mutually crossing concurrent reparent operations and leaf-to-parent conversion with existing memberships; no cycle or non-leaf membership commits.
- Reassign a product across incompatible trait schemas; old traits become ineligible until migrated or re-extracted.
- Apply an uncited human override; behavior matches the canonical CAP-4 decision and cannot silently become an ordinary evidenced trait.
- Expire/delete Phoenix traces after an unapplied stage outcome; one-time application still succeeds from application-owned data.
- Query a leaf containing CHF and EUR projection rows; the API returns partitioned results or a structured incompatibility, never one numeric ranking.
