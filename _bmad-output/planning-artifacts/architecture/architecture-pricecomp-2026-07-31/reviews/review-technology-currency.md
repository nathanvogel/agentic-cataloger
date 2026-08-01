# Reviewer Gate — Technology Currency and Integration

- **Artifact:** `../ARCHITECTURE-SPINE.md`
- **Re-review date:** 2026-07-31
- **Method:** fresh official-source checks, exact dependency resolution/import on CPython 3.14.6, API-signature inspection, and container-manifest checks
- **Supersedes:** the earlier review at this path

## Verdict

**PASS WITH ONE NON-BLOCKING CORRECTION.**

The revised spine closes every former gate failure. The PgQueuer/SQLAlchemy boundary is now an explicitly first-party producer-only bridge guarded by transaction and crash-window tests; the LangGraph Postgres checkpointer and pool are pinned and have lifecycle/configuration ownership; the FastMCP mount now binds the correct path, stateless transport, combined lifespan, host/origin policy, and contract test; PostgreSQL is pinned to 18.4 with the PostgreSQL 18 volume path; Phoenix's image, database, migration, retention, telemetry, and ELv2 exposure boundary are bound; and effective LangChain provider settings plus the CPython/Linux compatibility authority are explicit.

All exact application package pins resolve and import together on CPython 3.14.6. The exact uv 0.12.1 release artifact and both pinned container manifests exist. The only remaining correction is to name and pin the OTLP exporter that actually sends OpenTelemetry spans to Phoenix.

## Tier 0 — Blocking Findings

**None.**

## Tier 1 — Non-Blocking Correction

### TC-R1 — The telemetry stack still omits its concrete OTLP exporter

**Affected:** AD-12, AD-29, Stack.

The Stack now correctly pins OpenTelemetry API/SDK 1.44.0 and OpenInference LangChain instrumentation 0.1.68. Instrumentation creates/enriches spans; it does not provide the exporter that transmits them to Phoenix. AD-12 refers to “exporters,” but no exporter distribution or Phoenix OTel helper is named.

The smallest compatible closure is to pin one of:

- `opentelemetry-exporter-otlp-proto-http==1.44.0`, with the Phoenix OTLP `/v1/traces` endpoint configured explicitly; or
- a verified Python-3.14-compatible `arize-phoenix-otel` version, which wraps the SDK/exporter and Phoenix defaults.

`opentelemetry-exporter-otlp-proto-http==1.44.0` was resolved and imported with the spine's OpenTelemetry 1.44.0 and OpenInference 0.1.68 pins on CPython 3.14.6 during this review.

This is not a direction or integration blocker: the protocol boundary is already correct and the missing package is independently selectable. It should be added before the first telemetry implementation so a clean lock cannot silently produce spans that are never exported.

**Evidence:**

- [Phoenix Python tracing setup recommends `arize-phoenix-otel`](https://arize.com/docs/phoenix/tracing/how-to-tracing/setup-tracing/setup-using-phoenix-otel)
- [`opentelemetry-exporter-otlp` 1.44.0 package metadata](https://pypi.org/project/opentelemetry-exporter-otlp/1.44.0/)
- [Phoenix OTel helper and exporter API](https://arize.com/docs/phoenix/sdk-api-reference/python/arize-phoenix-otel)

## Closed Findings

### TC-01 — PgQueuer/SQLAlchemy transaction fit: closed

AD-22 now names `PgQueuerTransactionalProducer`, limits it to producers, requires it to unwrap the SQLAlchemy Psycopg physical connection, keeps consumers on PgQueuer's native driver, and prohibits dispatch-backed implementation until rollback, commit, and process-death tests pass.

That matches PgQueuer's maintainer-supported integration pattern. Enqueue is an INSERT on the same physical transaction; PostgreSQL defers the queue trigger's `pg_notify()` until commit. The bridge must not be used for consumers because the shim has no `LISTEN/NOTIFY`, which the revised rule now prevents. AD-23 binds Psycopg 3, avoiding an accidental `asyncpg` raw connection.

**Evidence:**

- [PgQueuer maintainer: enqueue-only SQLAlchemy/Psycopg transaction shim](https://github.com/janbjorge/pgqueuer/discussions/603)
- [SQLAlchemy `AsyncConnection.get_raw_connection()`](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncConnection.get_raw_connection)
- [PgQueuer driver requirements](https://github.com/janbjorge/pgqueuer/blob/main/docs/reference/drivers.md)

### TC-02 — LangGraph Postgres checkpoint package/config: closed

The Stack now pins `langgraph-checkpoint-postgres==3.1.1`, `psycopg-pool==3.3.1`, and `psycopg[binary]==3.3.4`. AD-21 binds `pipeline_run_id` to `thread_id`, a versioned workflow to checkpoint namespace, orchestration-only state, and strict serializer allowlisting. AD-29 assigns one-shot checkpointer setup before readiness. AD-31 requires checkpoint, migration, crash-window, and concurrency tests against PostgreSQL 18.4.

Version 3.1.1 exists and requires Python `>=3.10`, Psycopg, and psycopg-pool. Direct source inspection confirmed `AsyncPostgresSaver.from_conn_string()` creates its connection with `autocommit=True`, `prepare_threshold=0`, and `row_factory=dict_row`; this satisfies the package's documented table-setup and dictionary-row requirements and avoids prepared-statement incompatibility with transaction poolers if one is later introduced.

**Evidence:**

- [`langgraph-checkpoint-postgres` 3.1.1](https://pypi.org/project/langgraph-checkpoint-postgres/3.1.1/)
- [LangGraph checkpoint reference](https://reference.langchain.com/python/langgraph/checkpoints)

### TC-03 — FastMCP mounting/lifecycle/defaults: closed

AD-24 now exactly binds:

- `http_app(path="/", stateless_http=True)`;
- mount at `/mcp`, avoiding an accidental `/mcp/mcp`;
- combined MCP and application lifespans;
- strict trusted hosts/origins whenever network-reachable;
- curated tools;
- an initialize/list/call contract test under the lifespan.

FastMCP 3.4.5's live `FastMCP.http_app` signature was inspected and accepts `path`, `stateless_http`, `host_origin_protection`, `allowed_hosts`, and `allowed_origins`. Current FastMCP documentation requires forwarding the MCP app lifespan when mounted under FastAPI and documents stateless HTTP as the horizontally scalable mode. The revised rule matches those constraints.

**Evidence:**

- [FastMCP HTTP deployment and nested FastAPI mounting](https://gofastmcp.com/deployment/http)
- [FastMCP FastAPI integration](https://gofastmcp.com/integrations/fastapi)
- [FastMCP 3.4.5 package](https://pypi.org/project/fastmcp/3.4.5/)

### TC-04 — PostgreSQL 18 currency and container layout: closed

The Stack, AD-27, AD-29, and AD-31 now consistently bind PostgreSQL 18.4. AD-29 mounts the durable volume at `/var/lib/postgresql`, which is the official PostgreSQL 18 image volume; its default `PGDATA` is `/var/lib/postgresql/18/docker`. The `postgres:18.4` multi-platform manifest was resolved during this review.

PostgreSQL 18.4 is the current security-fixed release at review time. The revised pin removes the former moving-major-tag and wrong-volume risks.

**Evidence:**

- [PostgreSQL 18.4 release](https://www.postgresql.org/about/news/postgresql-184-1710-1614-1518-and-1423-released-3297/)
- [Official PostgreSQL image and 18+ `PGDATA` change](https://hub.docker.com/_/postgres/)

### TC-05 — LangChain provider defaults: closed

AD-25 now records immutable effective provider configuration: resolved model, structured-output method/schema/strictness, sampling, output limit, timeout, retry owner/count/backoff, streaming mode, and provider options. That is the correct abstraction because OpenAI, Anthropic, and Google adapters expose a common LangChain interface but retain different structured-output, retry, timeout, and request defaults.

The pinned adapter family resolves together with `langchain-core==1.5.3` and Pydantic 2.13.4 on CPython 3.14.6.

**Evidence:**

- [OpenAI structured-output contract](https://reference.langchain.com/python/langchain-openai/chat_models/base/ChatOpenAI/with_structured_output)
- [Anthropic structured-output contract](https://reference.langchain.com/python/langchain-anthropic/chat_models/ChatAnthropic/with_structured_output)
- [Google structured-output contract](https://reference.langchain.com/python/langchain-google-genai/chat_models/ChatGoogleGenerativeAI/with_structured_output)

### TC-06 — Required runtime packages/extras: substantially closed

The revised Stack now names:

- SQLAlchemy `[asyncio]`;
- Psycopg `[binary]`;
- psycopg-pool;
- `langgraph-checkpoint-postgres`;
- Uvicorn;
- OpenTelemetry API/SDK;
- OpenInference LangChain instrumentation.

The only remaining direct-runtime omission is TC-R1's exporter. No dependency conflict was found among the listed application packages.

### TC-07 — Phoenix version, license, persistence, and defaults: closed

Phoenix 19.11.1 exists, supports Python `>=3.10,<3.15`, and imports on CPython 3.14.6. The exact `arizephoenix/phoenix:version-19.11.1` container manifest exists.

AD-9 and AD-29 now bind:

- self-hosted Phoenix 19.11.1 under Elastic License 2.0;
- internal use only, excluding a third-party managed Phoenix feature;
- a dedicated PostgreSQL database and role;
- 30-day trace retention from first startup;
- product telemetry disabled;
- independent dataset/experiment persistence;
- a one-shot Phoenix migration before readiness;
- the exact versioned container image.

Those choices override Phoenix's live defaults of SQLite, indefinite retention, and enabled product telemetry. PostgreSQL 18.4 is above Phoenix's documented PostgreSQL 14+ floor. The ELv2 boundary is accurately represented.

**Evidence:**

- [Phoenix 19.11.1](https://pypi.org/project/arize-phoenix/19.11.1/)
- [Phoenix self-hosting images](https://arize.com/docs/phoenix/self-hosting)
- [Phoenix configuration and telemetry default](https://arize.com/docs/phoenix/self-hosting/configuration)
- [Phoenix data-retention defaults](https://arize.com/docs/phoenix/settings/data-retention)
- [Phoenix license](https://arize.com/docs/phoenix/self-hosting/license)

### TC-08 — CPython 3.14/runtime authority: closed

AD-27 now binds non-free-threaded CPython 3.14.6, uv 0.12.1, a committed `pyproject.toml` and `uv.lock`, Linux CI with PostgreSQL 18.4 as compatibility authority, and exclusion of LangGraph Server/CLI extras and application Pydantic V1 models.

The uv 0.12.1 release was published on 2026-07-31 at 19:43 UTC. Its Apple Silicon artifact executed successfully during this review. This resolves the apparent discrepancy from earlier search indexing, which still showed 0.12.0: the live official release and executable artifact are authoritative.

The complete application pin set resolved and imported on CPython 3.14.6:

- LangGraph 1.2.10
- `langgraph-checkpoint-postgres` 3.1.1
- PgQueuer 1.3.2
- SQLAlchemy `[asyncio]` 2.0.51
- Alembic 1.18.5
- Psycopg `[binary]` 3.3.4
- psycopg-pool 3.3.1
- FastAPI 0.141.1
- FastMCP 3.4.5
- Uvicorn 0.52.0
- `langchain-core` 1.5.3
- `langchain-openai` 1.4.1
- `langchain-anthropic` 1.5.3
- `langchain-google-genai` 4.3.2
- Pydantic 2.13.4
- OpenTelemetry API/SDK 1.44.0
- OpenInference LangChain instrumentation 0.1.68

This proves package existence, dependency coexistence, and import compatibility. AD-31 correctly assigns behavioral proof to Linux/PostgreSQL integration tests rather than treating imports as runtime proof.

**Evidence:**

- [uv 0.12.1 official release](https://github.com/astral-sh/uv/releases/tag/0.12.1)
- [Python 3.14.6](https://www.python.org/downloads/release/python-3146/)
- [LangGraph Python 3.14 support](https://github.com/langchain-ai/langgraph/pull/6298)

## Current-Version Ledger

| Technology | Revised pin | Result |
| --- | --- | --- |
| CPython | 3.14.6 | Exists; exact runtime used for resolution/import checks. |
| uv | 0.12.1 | Exists; official release artifact executed. |
| PostgreSQL | 18.4 | Current security-fixed release; container manifest exists. |
| LangGraph | 1.2.10 | Exists; imports on Python 3.14.6. |
| LangGraph Postgres checkpoint | 3.1.1 | Exists; imports; connection/setup defaults inspected. |
| PgQueuer | 1.3.2 | Exists; bridge matches maintainer-supported producer pattern. |
| SQLAlchemy `[asyncio]` | 2.0.51 | Exists; resolves with greenlet on Python 3.14.6. |
| Alembic | 1.18.5 | Exists and resolves with SQLAlchemy 2.0.51. |
| Psycopg `[binary]` | 3.3.4 | Exists; exact binary implementation imported. |
| psycopg-pool | 3.3.1 | Exists and satisfies checkpointer requirements. |
| FastAPI | 0.141.1 | Exists; imports on Python 3.14.6. |
| FastMCP | 3.4.5 | Exists; mount/security signature inspected. |
| Uvicorn | 0.52.0 | Exists; imports with revised stack. |
| LangChain packages | listed pins | Exist and resolve together. |
| Pydantic | 2.13.4 | Exists; imports on Python 3.14.6. |
| OpenTelemetry API/SDK | 1.44.0 | Exists and resolves with OpenInference pin. |
| OpenInference LangChain | 0.1.68 | Exists and imports with LangChain core 1.5.3. |
| Phoenix | 19.11.1 | Exists; imports under declared `<3.15` runtime bound. |
| Phoenix container | `version-19.11.1` | Exact manifest exists. |

## Gate Disposition

The spine is technology-current and integration-coherent enough to hand to implementation. TC-R1 should be corrected in the dependency manifest before telemetry work, but it does not require reopening any architecture decision.
