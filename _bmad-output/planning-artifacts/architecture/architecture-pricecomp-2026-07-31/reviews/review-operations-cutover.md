# Reviewer Gate — Operations, Brownfield, and Cutover

- **Artifact reviewed:** `../ARCHITECTURE-SPINE.md`
- **Review date:** 2026-07-31
- **Review mode:** clean reread of the revised spine against the current repository and selected vendor behavior
- **Lens:** executable topology; worker crash/retry; queue/checkpoint operations; migrations and vendor-owned schemas; PostgreSQL provisioning; retention; brownfield relocation; workspace rules; frontend/database cutover; rollback; operational deferrals

## Revised Verdict

**PASS WITH GATED CONDITIONS.**

The revised spine passes the operations/brownfield/cutover architecture gate for the first reversible bootstrap unit and subsequent implementation behind its named gates. It now makes the critical architectural commitments that were previously absent:

- a reversible bootstrap change precedes Python implementation;
- PostgreSQL 18.4 is the Linux CI authority and uses the PostgreSQL 18 volume root;
- application, Phoenix, and legacy data use separate databases and roles;
- Alembic, PgQueuer, LangGraph, and Phoenix have separate migration ownership and an explicit one-shot order;
- transactional dispatch is blocked until the physical-transaction bridge survives rollback, commit, and process-death tests;
- application retry states, replay identity, stage-attempt identity, terminal outcomes, and retry defaults are defined;
- cutover requires evidence, a restore/routing rehearsal, an observation window, and a no-reverse-migration rollback policy;
- sustained ingest, non-local data, shared deployment, internal staging, frontend migration, and public exposure each have explicit decision gates.

This is not an unconditional production-readiness verdict. The unresolved items below are implementation contracts intentionally left behind gates. Crossing a gate without binding its listed details invalidates this pass.

## Current Repository Reality

The repository remains entirely pre-bootstrap:

- `docker-compose.yml` still runs a floating `postgres:18-alpine` service with one database and one credential.
- There is no Dockerfile, Devcontainer, `pyproject.toml`, `uv.lock`, or CI workflow.
- `/backend` remains NestJS/Yarn, `/data-importer` remains a separate Yarn application, and `/frontend` remains bound to the legacy integer-ID/flat-category OpenAPI contract.
- Current always-applied rules still require Yarn, TypeScript, NestJS, and Zapatos.
- The legacy importer still resolves its default data path relative to its compiled location and overwrites `attributes` during upsert.
- Current SQL bootstrap and migration scripts still operate one `pricecomp_db` database manually.

These facts no longer contradict the architecture because AD-27 explicitly makes their relocation and correction the first reversible unit before Python implementation. They remain acceptance evidence the bootstrap unit must produce.

## Determinations That Now Pass

### PostgreSQL 18.4 topology

The `postgres:18.4` official image exists for Linux AMD64 and ARM64. For PostgreSQL 18 images, mounting the durable volume at `/var/lib/postgresql` is correct because version-specific `PGDATA` lives below that root. AD-27 and AD-29 therefore pin an executable database version and avoid the current floating-tag ambiguity.

One PostgreSQL instance with separate application, Phoenix, and frozen-legacy databases is acceptable for this scale. Keeping PgQueuer and LangGraph tables in the application database preserves transactional dispatch and checkpoint locality while AD-23 prevents Alembic from claiming vendor ownership.

### Migration authority and order

AD-29 now states a valid dependency order:

1. database and role bootstrap;
2. Alembic application migrations;
3. PgQueuer install/upgrade;
4. LangGraph checkpointer setup;
5. Phoenix migration using the pinned Phoenix image;
6. service readiness.

The diagram correctly gives Phoenix migration a separate one-shot role against the Phoenix database. `langgraph-checkpoint-postgres` 3.1.1 requires explicit checkpointer setup and supports the strict MessagePack restriction adopted by AD-21. Phoenix 19.11.1 supports a separate `phoenix db migrate` invocation.

### Worker retry and replay model

AD-21, AD-22, AD-30, AD-31, and AD-34 now form a coherent model:

- `pipeline_run_id` survives infrastructure retry and keys the LangGraph thread;
- each provider invocation has a distinct `stage_attempt_id`;
- validated outcomes/configuration are durable before one-time command application;
- application idempotency is payload-bound and outlives queue/checkpoint replay;
- fenced compare-and-set transitions protect terminal states;
- deterministic invalid/defer is separated from retryable infrastructure failure;
- dispatch use is blocked until atomic enqueue, concurrency, SIGKILL recovery, cancellation, propagation, and terminal disposition are proven.

This correctly treats PgQueuer as at-least-once dispatch rather than exactly-once business execution.

### Cutover and rollback policy

AD-15 now supplies the essential semantic policy:

- replay starts from an immutable source manifest rather than migrating legacy AI state;
- reconciliation, capability, invariant, eval, OpenAPI/frontend, end-to-end, restore, and routing evidence gate the switch;
- the new database remains authoritative and preserved during the observation window;
- routing rollback pauses operator writes and does not reverse-migrate into legacy;
- recovery becomes forward-only after the declared observation window.

That is a defensible rollback boundary. It avoids the unsafe promise that two incompatible taxonomies can be bidirectionally synchronized.

### Operational deferrals

The Deferred section now uses enforceable latest-decision points rather than generic “later” language:

- dispatch proof before any dispatch-backed feature;
- review lifecycle before review schema/UI implementation;
- queue/checkpoint maintenance and operations before sustained ingest;
- CI/release decisions before CI implementation;
- configuration/secrets before shared deployment;
- backup/recovery before first non-local data;
- provider/IaC/pooling/autoscaling before internal staging;
- authentication and threat modeling before public exposure.

Those are appropriate architecture gates. Public production is explicitly prohibited rather than implied to be ready.

## Tier 1 — Bind During the Reversible Bootstrap

### OP-R1 — The bootstrap unit still needs an explicit acceptance manifest

AD-27 correctly makes bootstrap first, but “relocates legacy code, fixes paths/scripts, and updates rules/documentation” leaves success open to interpretation. The bootstrap work item should bind:

- exact `git mv` destinations and preserved lockfiles;
- path-scoped workspace rules for `/backend`, `/frontend`, and `/legacy/**`;
- corrected Husky/root assumptions after nesting;
- an explicit catalog-data path for `/legacy/data-importer`, because its current `../../data` default will resolve to `/legacy/data`;
- build/test commands and successful evidence for both relocated Yarn packages;
- a legacy API smoke test against the frozen-compatible database;
- root setup documentation that identifies old and new commands without ambiguity;
- proof that no Python domain implementation is mixed into the relocation change.

Without this manifest, the intended reversible unit can become an unreviewable relocation-plus-rewrite.

### OP-R2 — Transition host routing and port ownership remain unspecified

AD-29 requires Compose to run both the new API and relocated legacy API, while the current frontend calls the legacy API at port 3010. The spine does not assign distinct host ports or a routing/proxy mechanism. The bootstrap/Compose contract must name:

- legacy API host/container port;
- new API host/container port;
- which endpoint the frontend uses before and after switch;
- how the routing rehearsal changes that endpoint atomically;
- whether Phoenix and MCP are host-exposed or container-network-only;
- how CORS/trusted-host settings differ before and after cutover.

This is the remaining concrete brownfield topology seam; two APIs cannot both inherit the current host binding.

### OP-R3 — Database bootstrap needs a least-privilege role and schema manifest

AD-29 names separate databases/roles and migration order but not the privilege boundaries required to implement them. Before the new Compose bootstrap is written, bind:

- database names and owners;
- bootstrap/admin, application migration, application runtime, Phoenix migration/runtime, and legacy read-only roles;
- whether PgQueuer and LangGraph use `public` or separate vendor schemas;
- `search_path`, grants, default privileges, connection limits, and ownership of created tables;
- which one-shot role receives database-creation authority;
- confirmation that API/worker and Phoenix runtime credentials cannot create databases or run arbitrary migrations.

The backend `migrate` role should not retain cluster-admin credentials merely because database/role bootstrap runs first.

### OP-R4 — Vendor migration commands need executable preconditions

The order is correct, but the migration contract still needs exact commands and connection behavior:

- PgQueuer install versus upgrade detection and idempotency;
- LangGraph `AsyncPostgresSaver.setup()` with required autocommit and row-factory behavior;
- strict MessagePack configuration during both setup verification and runtime;
- Phoenix migration from the exact pinned Phoenix image;
- lock/statement timeouts, failure propagation, and readiness refusal on a stale migration head;
- clean-database and upgrade-from-previous-version tests.

These details belong in the migration/CI contract, not in application startup. Runtime API/worker processes must never opportunistically acquire DDL authority.

## Tier 2 — Bind Before Dispatch or Sustained Ingest

### OP-R5 — The central retry policy must map explicitly onto PgQueuer controls

PgQueuer does not infer the adopted application policy. Ordinary unhandled exceptions become terminal unless handlers use explicit `RetryRequested` or `DatabaseRetryEntrypointExecutor`; terminal jobs are deleted from the active queue unless `on_failure="hold"` is selected.

The dispatch gate must specify:

- which exception classifier raises durable retry;
- whether the database retry executor is used;
- exact attempt semantics, because “five attempts” can mean five total executions or five retries;
- `on_failure="hold"` versus an application-owned durable failed-work record;
- heartbeat timeout, initial delay, multiplier, full-jitter implementation, and 15-minute cap;
- the single retry owner for provider calls so provider SDK, LangChain, workflow, and queue retries do not multiply invisibly.

AD-25 records retry ownership; the gate must prove only the recorded owner actually retries.

### OP-R6 — Running cancellation requires an intermediate protocol

The application states include `cancelled` but no explicit `cancel_requested`. Immediate transition of running work to `cancelled` is insufficient unless the worker is also prevented from invoking further providers and committing later stage outcomes.

The cancellation proof should bind:

- request, acknowledgment, and terminal transition semantics;
- queue cancellation for pending/retry-wait work;
- cooperative cancellation checks around provider calls and command application;
- fencing behavior for late worker completion;
- treatment of an uncancellable in-flight provider request and its cost trace;
- cancellation of all candidate runs derived from one ingest-selection manifest;
- checkpoint retention/deletion after cancellation.

This is already correctly gated before dispatch reliance; it remains unresolved implementation work.

### OP-R7 — Terminal failure needs one authoritative operator view

AD-22 says exhausted work remains inspectable/requeueable, but it does not choose whether the authoritative terminal payload lives in application work tables, held PgQueuer rows, or both. Duplicating operator truth across an application `failed` state and vendor-held job can produce divergent requeue actions.

Select one authoritative requeue command and define how it:

- preserves prior attempts and failure reason;
- allocates the next infrastructure attempt/run identity;
- resets or retains PgQueuer's vendor attempt counter;
- handles changed configuration or payload;
- records operator/reason/timestamp;
- avoids conflating infrastructure failure with domain `deferred_items`.

PgQueuer logs can remain audit evidence without becoming the domain/operator source of truth.

### OP-R8 — Queue/checkpoint cleanup boundaries are gated but not yet designed

The gate placement before sustained ingest is correct. Its contract still needs to cover:

- active, held, terminal-log, and canceled queue retention;
- checkpoint retention by whole `pipeline_run_id`/namespace;
- protection of retryable, review-linked, and observation-window runs;
- orphan reconciliation among application run, PgQueuer job, and LangGraph thread;
- cleanup batch size, lock timeout, statement timeout, and retry;
- autovacuum/analyze expectations for queue/log/checkpoint tables;
- disk, dead-tuple, oldest-job, and oldest-checkpoint alerts;
- backup inclusion or deliberate exclusion for rebuildable vendor state.

No sustained catalog replay should begin before those values and operator commands exist.

### OP-R9 — Worker shutdown and deployment compatibility remain open

The operations gate should bind SIGTERM drain time, SIGKILL recovery expectation, maximum provider-call duration, heartbeat behavior during long calls, and readiness/liveness semantics. It must also decide whether old and new workers can overlap.

Because checkpoint namespace includes a workflow version, incompatible graph code can be isolated, but the deployment contract must define whether old workflow versions remain runnable until their jobs finish or are explicitly migrated/failed. A deployment must not strand a retryable checkpoint whose code version has disappeared.

### OP-R10 — Phoenix retention needs enforcement and outage behavior, not only a default

The adopted 30-day default is executable through `PHOENIX_DEFAULT_RETENTION_POLICY_DAYS=30`, and telemetry can be disabled with `PHOENIX_TELEMETRY_ENABLED=false`. Remaining operational work is to:

- verify those settings before first trace;
- detect per-project retention overrides, which Phoenix permits;
- prove weekly cleanup executes and monitor cleanup age/storage;
- state whether deleted raw traces may still be referenced by `deferred_items`;
- define backup treatment for datasets/experiments versus disposable raw traces;
- define non-blocking exporter/backpressure behavior when Phoenix is down;
- ensure business commits never depend on successful trace export.

These belong in the configuration and operations contracts before sustained ingest.

## Tier 3 — Bind Before Shared Deployment, Cutover, or Internal Staging

### OP-R11 — The cutover runbook still needs concrete values and ownership

AD-15 supplies the correct policy but intentionally leaves runbook values open. Before migration, bind:

- who freezes legacy writes, accepts each evidence report, authorizes switch, and declares rollback;
- exact source reconciliation tolerances and applicable capability/eval thresholds;
- observation-window duration and rollback decision deadline;
- routing mechanism and propagation verification;
- quiescing/canceling in-flight new-system jobs before routing rollback;
- read-only user behavior while operator writes are paused on rollback;
- preserved new-database backup/reference for forward recovery;
- legacy retirement/tombstone evidence after the window.

The timed rehearsal must use the same routing and restore mechanism intended for cutover, not a verbal walkthrough.

### OP-R12 — Frontend migration still needs an internal-access topology

The current frontend is browser-delivered, calls `VITE_BACKEND_URL`, sends credentials, and uses integer IDs. Before frontend migration, define:

- how an operator browser reaches an internal-only API;
- TLS/origin/CORS/credential behavior;
- new UUID/tree/review-action OpenAPI generation and contract pinning;
- atomic frontend/API routing switch;
- cache invalidation and stale old-tab behavior at switch;
- behavior during the rollback read-only period.

AD-32 correctly prohibits public unauthenticated deployment. The frontend gate must not accidentally bypass that boundary by publishing an internal mutation endpoint.

### OP-R13 — Backup/recovery and CI/release gates need recorded evidence artifacts

The deferral points are correct, but passing them should produce durable artifacts rather than undocumented settings:

- encrypted backup cadence, retention, restore procedure, measured RPO/RTO, and latest restore-drill result for application, Phoenix, and legacy databases;
- clean-checkout Linux CI using PostgreSQL 18.4 and the same `api`, `worker`, and `migrate` commands;
- migration failure tests, crash-window tests, image digest/SBOM, and artifact promotion record;
- configuration inventory with secret source, role consumer, validation/default, log-redaction rule, catalog mount, and provider quota policy.

The cutover evidence bundle should reference immutable CI artifacts, database backup identities, source manifest checksum, frontend build, and image digests.

### OP-R14 — Internal staging remains intentionally blocked

Provider, autoscaling, connection pooling, scheduler/IaC, secrets, and operations ownership remain unresolved by design. The “before internal staging” gate is correctly placed and must not be weakened to “before public production.” Connection budgets must account for API, every worker, PgQueuer, LangGraph, migration jobs, Phoenix, and operator access against the one PostgreSQL instance.

Public production remains a separate no-go until authentication, authorization, and threat modeling are complete.

## Gate Conditions

The architecture pass remains valid only under this execution order:

1. Complete and verify the reversible relocation/rules/documentation bootstrap.
2. Bind PostgreSQL databases, roles, schemas, ports, and one-shot migration commands.
3. Build fresh-database Compose/Devcontainer topology using pinned PostgreSQL 18.4 and Phoenix images.
4. Prove the transactional producer and full dispatch failure matrix before enabling any dispatch-backed feature.
5. Bind operations, retention, cleanup, and reconciliation before sustained ingest.
6. Bind configuration/secrets and backup/recovery before shared deployment or first non-local data.
7. Bind frontend topology and the concrete cutover runbook, then rehearse restore/routing rollback.
8. Resolve provider, pool, scaling, IaC, and operational ownership before internal staging.
9. Complete security/auth work before any public API, MCP, Phoenix, or review UI exposure.

No unresolved finding requires changing the selected modular-monolith, PostgreSQL, PgQueuer, LangGraph, Phoenix, or side-by-side cutover direction. The remaining work is appropriately gateable, provided the gates are enforced as prerequisites rather than treated as backlog suggestions.
