# Revised Adversarial Seam Review — Architecture Spine

**Artifact attacked:** `ARCHITECTURE-SPINE.md`, reread from scratch after reviewer-gate revision  
**Lens:** Two teams independently build units one level below the spine. A finding survives only when both units can obey every applicable AD literally and still fail to compose or produce non-equivalent business meaning.

## Revised verdict

**FAIL — substantially improved, but not yet safe for unconstrained parallel implementation.**

The revision closes most previous blocker classes. AD-34 establishes a shared contract owner; AD-4/6 bind evidence to immutable observations and replace presentation-based source identity; AD-21 separates selection manifests, candidate runs, and provider attempts; AD-22/30 define retry and idempotency foundations; AD-4/13/30 define a revision-linked comparison projection; AD-12 supplies a telemetry convention; AD-17 adds taxonomy generations and fencing; and the deferred section now places operational stop gates.

The surviving failures are narrower. They concern meanings still left implicit inside otherwise shared shapes, and coordination protocols that are named but not fully specified. The pairs below remain literally compliant.

## Tier 0 — Remaining build-blocking seams

### 1. `stage_attempt_id` still conflates provider invocation, stage execution, and command application

- **Unit A:** Creates one `stage_attempt_id` for every provider invocation. In an O5 tool loop, only the final invocation's attempt stores the validated stage outcome and becomes the idempotency anchor for command application.
- **Unit B:** Also creates an attempt for every provider invocation, but records the aggregate stage outcome against a synthetic stage execution record and links every provider attempt to it; command application is keyed by that execution rather than the final call.
- **Both comply:** Every new provider invocation has a new attempt ID; the candidate run survives infrastructure retry; outcome/config data is durable before one-time command application; all stage outcomes use AD-34 (AD-21/34).
- **Collision:** `pipeline`, telemetry, evaluator, and command units disagree about which ID owns the outcome, which attempt E2 scores, and which key proves the business effect was applied once. Tool loops and multi-call stages cannot be reconstructed from a model that only defines run and provider-attempt identity.
- **Required closure:** Add a distinct `stage_execution_id` and define its one-to-many relation to provider attempts, the controlling/final outcome, command receipt, replay key, telemetry spans, and E2 example. State whether non-LLM deterministic stages also receive executions and attempts.

### 2. Comparison projection invalidation has no generation, fencing, or freshness contract

- **Unit A:** Every price, quantity, membership, or unit-policy command transactionally deletes affected projection rows. A worker rebuilds missing rows and uses source-revision compare-and-set before insert.
- **Unit B:** Commands upsert projection-invalidation records and retain old projection rows. A worker rebuilds by invalidation generation; queries exclude rows whose revision tuple is not current.
- **Both comply:** Comparison alone owns the rebuildable projection; commands atomically write projection invalidation; rows carry exact source revisions/formula version; current reads use the projection; owner tables remain authoritative (AD-4/13/14/30).
- **Collision:** A mutation producer written for delete semantics emits no work B's worker can claim; a producer written for request semantics leaves A's query serving or hiding the wrong rows. Concurrent rebuilds can let an older calculation overwrite a newer one unless every implementation independently invents the same fence.
- **Required closure:** Define the projection invalidation envelope, affected-scope expansion, uniqueness, requested/processing generations, lease/fence, source-revision CAS, completion rule, query-time freshness predicate, and behavior while current projection data is unavailable. Include category merge/reparent and conversion-registry rollout.

### 3. Quantity precedence is required but not defined

- **Unit A:** For a product with both `net_content = 500 g` and source `price_basis = CHF 0.40 / 100 g`, selects net content first for fixed packages and calculates from shelf price.
- **Unit B:** Selects compatible `price_basis` first because it is directly stated by the source, using net content only when no basis exists.
- **Both comply:** Each uses typed quantity kinds, a versioned unit registry, deterministic precedence, exact source revisions, the fixed-content formula, and direct price-basis conversion without inventing package content (AD-4/30).
- **Collision:** The same valid observation produces different accepted quantity revisions and normalized prices. Review, projection, and E2 units cannot infer which result is authoritative from the contracts named in AD-34.
- **Required closure:** Publish the complete selection order and conflict table across reviewed override, deterministic/inferred values, `net_content`, `item_count`, and `price_basis`; define compatibility, tie-breaking, supersession, and defer reason codes. Put its immutable version in the stage outcome and projection.

### 4. Parent-widen comparison semantics remain undefined

- **Unit A:** A parent is comparison-eligible only when it declares its own preferred comparable unit; otherwise widening returns a typed “not comparable” result.
- **Unit B:** A parent always widens scope, partitions descendant leaves by compatible unit dimension, and returns several comparison groups when no parent unit exists.
- **Both comply:** Parents widen comparison, leaves require preferred units, no conversion is fabricated, and every result states currency/unit (AD-3/4/30 and CAP-3/5). No AD requires every parent to declare one unit or says widening must return one result set.
- **Collision:** The comparison API, frontend, and eval cases disagree on whether the same parent request is invalid, one result set, or multiple grouped sets.
- **Required closure:** Define parent comparison eligibility, inherited versus explicit policy, mixed-dimension handling, secondary-unit behavior, output cardinality, and the exact typed error/defer result.

### 5. Taxonomy revision preconditions have no common scope

- **Unit A:** Uses one global taxonomy revision on every assign, merge, and reparent command. This serializes taxonomy writes and makes cycle validation stable.
- **Unit B:** Uses category/root-scoped revisions plus deterministic advisory locking of affected paths. It preserves concurrency while preventing write-skew and cycles.
- **Both comply:** Commands carry expected taxonomy revisions; stale writes reject/defer; the database and command validation preserve one rooted acyclic tree and one active membership; repair commands also carry AD-17 fencing tokens (AD-3/14/17/23).
- **Collision:** Pipeline, review, and hygiene command producers cannot construct the other's precondition. AD-34 owns command/query results but does not fix mutating command request contracts or the meaning/cardinality of “taxonomy revisions.”
- **Required closure:** Add command requests to `contracts/v1` and define the revision vector required by each taxonomy operation, how it is read, locking/CAS expectations, interaction with repair fencing, and stale-result/re-drive behavior.

## Tier 1 — Remaining cross-unit contract holes

### 6. `EvidenceRef` lacks canonical offset and hash semantics

- **Unit A:** Stores Python Unicode code-point offsets into NFC-normalized field text and hashes UTF-8 bytes with SHA-256.
- **Unit B:** Stores UTF-8 byte offsets into the immutable pre-normalization decoded field and uses BLAKE3 over length-prefixed field bytes.
- **Both comply:** The shared value has field, verbatim span, offsets, text hash, immutable observation, and extractor/config version (AD-4/34). Source normalization remains adapter-versioned (AD-6).
- **Collision:** Enrichment accepts evidence that review rejects for multilingual text, combining marks, or repeated spans. Sharing the same integer/string fields does not make their interpretation shared.
- **Required closure:** Define source-text decoding and normalization, offset unit and interval convention, hash algorithm and exact byte preimage, field addressing, repeated-span behavior, and conformance fixtures containing DE/FR/IT text and composed/decomposed Unicode.

### 7. Source namespace and identity-policy evolution can split one product

- **Unit A:** A Coop adapter owns namespace `coop`, treats retailer SKU as `source_product_id`, and puts package code in `source_variant_id`.
- **Unit B:** Its successor owns namespace `coop_ch`, prefers GTIN as `source_product_id`, and encodes package code inside that ID.
- **Both comply:** Each uses a stable typed source identity, versioned adapter policy, explicit failures for missing/colliding IDs, immutable snapshots, and deterministic replay (AD-6/26/34).
- **Collision:** An adapter upgrade creates new application products instead of new observations of existing products. The approved replay manifest can detect count drift but provides no architecture rule for namespace allocation, identity-policy continuity, aliases, or an intentional identity migration.
- **Required closure:** Establish a source-namespace registry and ownership rule, stable-ID precedence per source, variant semantics, adapter-policy compatibility classes, and a command/gate for identity-policy migration. Forbid policy upgrades that silently change existing source identities.

### 8. Snapshot completeness does not name its coverage scope

- **Unit A:** Marks a snapshot `complete` when it contains the retailer's entire catalog; explicit absence may deactivate any missing source identity in the namespace.
- **Unit B:** Marks a filtered source-category export `complete` for that filter and applies absence only inside the declared category.
- **Both comply:** Each snapshot has observed time, checksum, adapter version, completeness, deterministic order, and explicit absence policy; filtered ingest is supported (AD-2/6).
- **Collision:** If `CatalogSnapshotRef` carries only a completeness flag/policy label without a canonical coverage expression, catalog ingestion can deactivate the whole namespace or fail to deactivate anything. “Complete” is true in both units but means different sets.
- **Required closure:** Make coverage a first-class immutable contract: namespace, selection predicate/manifest identity, whether it is authoritative, expected/committed counts, and exact absence scope. Define overlap and supersession across full and filtered snapshots.

### 9. Idempotency does not define logical caller or child-key derivation

- **Unit A:** Uses inbound adapter (`rest`, `mcp`, `worker`) as `caller`; workflow child keys include `stage_attempt_id`, so a genuinely new provider invocation may apply a new outcome.
- **Unit B:** Uses operator/service identity as `caller`; child keys use `(pipeline_run_id, item_id, stage_name, config_version)`, so all attempts for the logical stage converge on one terminal result.
- **Both comply:** Keys are scoped by `(command_type, caller, key)`, bind a canonical payload hash, atomically record results/effects, reject changed payloads, and outlive replay (AD-14/22/30).
- **Collision:** The same operator request through REST and MCP may execute twice in A but dedupe in B. A retry producing a new valid outcome is allowed by A and rejected as changed payload by B. Pipeline and command units disagree about “one-time command application.”
- **Required closure:** Define caller namespaces in an unauthenticated internal system, cross-adapter caller propagation, canonical payload encoding/hash algorithm, and deterministic key derivation for submission, stage execution, provider attempt, command application, re-drive, and manual requeue.

### 10. Failure classification and retry ownership remain semantically open

- **Unit A:** A provider's schema-invalid structured output is an `invalid` stage outcome and never infrastructure-retries; an SDK's internal HTTP retry is part of one provider invocation/attempt.
- **Unit B:** The same schema failure is `retryable_failure` within the configured model-attempt budget; every SDK HTTP attempt is a new provider invocation and `stage_attempt_id`.
- **Both comply:** Deterministic invalid/defer does not use AD-22 infrastructure retry; effective configuration records retry owner/count/backoff; each new invocation is identified under its own interpretation (AD-21/22/25/34).
- **Collision:** Identical effective run configurations produce different call counts, costs, attempt histories, and terminal stage outcomes. This can confound CAP-10 even when workflow/supply arms are nominally controlled.
- **Required closure:** Publish a failure taxonomy mapping provider/network/rate-limit/timeout/schema/validation/tool errors to stage outcomes and retry owner. Define what counts as an invocation beneath LangChain/SDK retries and require adapters to expose every billable call consistently.

### 11. Batched telemetry attribution is “explicit” but not interoperable

- **Unit A:** Emits one leaf LLM span per P10 provider call with `pricecomp.item.ids` as an ordered array and no singular item ID.
- **Unit B:** Emits one leaf LLM span per provider call, adds span links or child item spans each carrying required `pricecomp.item.id`, and keeps the provider span item-neutral.
- **Both comply:** A leaf represents exactly one provider call, parent spans carry stage/run scope, batched attribution is explicit, and required IDs/config versions are emitted under `pricecomp.telemetry.v1` (AD-12).
- **Collision:** Evaluation and Phoenix queries written for one representation cannot join per-item E2 outcomes from the other. The rule requires singular `pricecomp.item.id` while allowing batched provider calls but does not specify the canonical bridge.
- **Required closure:** Fix the exact batch representation, attribute/event/link keys and types, item ordering, duplicate-item rules, relation to `stage_execution_id`, and reference Phoenix queries/fixtures for P2 and P10.

### 12. The MCP capability surface is behaviorally constrained but not interface-versioned

- **Unit A:** Exposes `search_categories`, `create_category`, `assign_product`, and `extract_traits` with flat curated arguments.
- **Unit B:** Exposes the same required capabilities as namespaced tools (`taxonomy_search`, `taxonomy_create`, etc.) with a common request envelope and polling token.
- **Both comply:** Tools are curated, not OpenAPI-generated; both use the same commands, results/errors, idempotency, telemetry, stateless mount, and initialize/list/call lifecycle contract (AD-5/24/31/34 and SPEC O1).
- **Collision:** LangGraph prompts/tool bindings built independently against A cannot call B. The existing contract test proves mounting and invocation behavior, not the stable names, descriptions, schemas, or compatibility policy that model-facing clients consume.
- **Required closure:** Publish a versioned MCP tool manifest with stable names, descriptions, argument/result schemas, async/poll behavior, deprecation rules, and prompt/tool-binding contract tests. Do the equivalent for REST paths/status codes before frontend work, as already required by the cutover gate.

## Tier 2 — Operational and lifecycle holes

### 13. Cancellation has a state but no business-effect guarantee

- **Unit A:** Cancellation is cooperative. An in-flight command may commit; the fenced worker then records `cancelled`, and the result reports committed effects.
- **Unit B:** Cancellation fences all later command application. Provider cost may already be incurred, but no post-cancel business mutation can commit.
- **Both comply:** Work uses the declared monotonic state set; late workers cannot regress terminal state; REST/MCP support cancellation and handlers remain replay-safe (AD-22/31).
- **Collision:** A caller seeing `cancelled` cannot know whether product, taxonomy, deferred, projection, or queue effects exist. Tests can assert the same terminal enum while the domain guarantee differs.
- **Required closure:** Define cancellation request versus terminal cancellation, linearization point, allowed in-flight effects, command fence behavior, child-job propagation, projection/review cleanup, and a mandatory effect receipt.

### 14. Replay may depend on a Phoenix payload that expires

- **Unit A:** Stage attempts persist the full validated AD-34 outcome in application Postgres, so replay never needs raw Phoenix data.
- **Unit B:** Uses AD-21's allowed “provider response reference,” storing a Phoenix trace/span reference and reconstructing the outcome on replay. Phoenix raw traces expire after 30 days.
- **Both comply:** The stage attempt durably stores an outcome or response reference; Phoenix is the sole trace store; raw traces use 30-day retention; application records remain authoritative for work state (AD-9/21).
- **Collision:** B cannot replay after trace expiry, while A can. Deferred review, manual requeue, or orphan reconciliation may outlive the trace unless queue/checkpoint/stage-attempt retention is guaranteed shorter.
- **Required closure:** Require a durable validated contract outcome/command receipt in application state, or cap every possible replay/requeue horizon below trace retention and specify terminalization before deletion. A reference to an expiring trace must not be the only replay source.

### 15. Contract versioning lacks deployment and queued-payload compatibility rules

- **Unit A:** Drains all jobs and deletes compatible checkpoints before deploying `contracts/v2`; API and worker only understand their current contract version.
- **Unit B:** Performs a rolling API/worker deployment and supports N/N-1 stage/job envelopes with explicit upcasters.
- **Both comply:** Shared contracts are versioned; one image exposes roles; workflow checkpoint namespace is versioned; production topology is deferred (AD-21/29/34).
- **Collision:** During separate API/worker rollout or recovery of an old job/checkpoint, a v2 producer can feed a v1-only worker. No rule says whether drain, dual-read, upcast, dead-letter, or migration is mandatory.
- **Required closure:** Define supported-version windows, producer/consumer rollout order, persisted envelope discriminators, upcaster ownership, checkpoint/job drain or migration, rollback compatibility, and the release test matrix.

### 16. Operational gates are well placed but not executable

- **Unit A:** A release controller treats the PgQueuer gate as passed when the named tests exist and interprets “sustained ingest” as more than one catalog; it allows shared staging before backup RPO/RTO is set because staging is not production.
- **Unit B:** Requires recorded passing artifacts for the exact image/database versions, treats any scheduled ingest as sustained, and classifies shared staging as non-local data requiring backup/restore evidence.
- **Both comply:** Each can honestly claim to honor the prose “before feature,” “before sustained ingest,” “before shared deployment,” “before first non-local data,” and “before internal staging” gates in AD-15/22 and Deferred.
- **Collision:** Release, migration, and operations units open capabilities at different times. A gate that lacks an ID, owner, objective predicate, evidence location, expiry/version binding, and fail-closed enforcement is advisory, not a compatibility boundary.
- **Required closure:** Create a versioned gate registry covering dispatch, review lifecycle, queue/checkpoint maintenance, CI/release, configuration/secrets, backup/restore, operations, staging/deployment, security, cutover, and retirement. For each, define owner, prerequisite, exact evidence, environment scope, image/schema versions, expiration/revalidation, and the command that refuses progress when unmet.

## Findings retired by the revision

The prior review's broad findings about missing shared values/stage statuses, presentation-based source identity, unrevisioned evidence, unscoped idempotency, mutable configuration labels, ambiguous E3 denominator, generic telemetry keys, unfenced taxonomy review generations, stale quantity-row price caches, and unconstrained REST/MCP behavior are retired. The revised ADs address them materially; they are not repeated as stale findings.

The first-party review lifecycle remains intentionally unresolved, but it is not counted above as a current implementation seam because the revised spine explicitly prohibits review schema/UI implementation until uniqueness, transitions, retry/cancel, re-drive target, and evidence promotion are bound. It remains safe only if the operational gate in finding 16 is made fail-closed.

## Gate result

The architecture can support parallel implementation after the Tier 0 contracts are added and the operational gate registry prevents gated packages from starting early. Until then, independently compliant units can still disagree on stage identity, projection freshness, quantity choice, parent widening, and taxonomy revision preconditions; those are business-semantic incompatibilities, not adapter details.
