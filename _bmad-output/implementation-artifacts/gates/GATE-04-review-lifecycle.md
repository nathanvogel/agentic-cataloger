# GATE-04: First-party review lifecycle

**Status:** bound (2026-08-01)  
**Blocks:** Story 3.1 (schema), Story 5.1 (read API), Epic 5 UI  
**Evidence location:** Alembic migration + contract test (no mutating routes)

## MVP posture (binding)

Read-only operator surface (CAP-9 / AD-8). **No** in-app reviewer domain writes. Re-drive by **CLI only**.

## Table: `deferred_items` (binding)

Owner package: `review`.

| Column | Type | Rule |
|--------|------|------|
| `id` | UUIDv7 | PK |
| `product_id` | UUIDv7 | FK catalog product |
| `pipeline_run_id` | UUIDv7 | nullable until Epic 4 |
| `stage` | enum | pipeline vocabulary (`assign`, `extract`, …) |
| `reason_code` | enum | `unknown`, `defer`, `low_confidence` |
| `attempt_count` | int | starts at 1 |
| `payload_snapshot` | jsonb | immutable after insert |
| `trace_id` | text | nullable; Phoenix URL derived at read |
| `status` | enum | `open`, `resolved`, `cancelled` |
| `created_at` | timestamptz | sort newest first |

## Uniqueness (binding)

At most one **open** row per `(product_id, stage, reason_code)`.

Re-defer same triple → increment `attempt_count`, update `trace_id` if present; **no** new row.  
`payload_snapshot` is never updated.

## Status transitions (binding)

```
open --re-drive--> open (attempt_count++)
open --success--> resolved
open --cancel--> cancelled   (CLI only)
```

## Re-drive (binding)

- CLI → same command handler as pipeline (`RedriveDeferredItem`)
- Enqueue after commit (GATE-03)
- Idempotency: `(command_type=redrive, caller=cli, key=deferred_item_id)`

## Read API (binding — Story 5.1)

| Route | Method |
|-------|--------|
| `/api/v1/deferred` | GET — filters `stage`, `reason` (AND); order `created_at DESC` |
| `/api/v1/deferred/{id}` | GET — payload + optional `evidence_span` |
| *(none)* | POST/PATCH/DELETE forbidden in MVP |

New API base: `http://localhost:3020` (not legacy `:3010`).

## Frontend (binding — Epic 5)

- Route: `frontend/app/routes/deferred.tsx` (inside existing app)
- Mock reference: `ux-designs/.../mockups/deferred-list.html`

## Story checklist (implementation fills these)

- [ ] Migration matches column/uniqueness rules
- [ ] Story 3.1 AC satisfied
- [ ] Read API contract test: no write routes
- [ ] Story 5.1 lists/filters match GATE-04
